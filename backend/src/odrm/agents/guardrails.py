from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

from pydantic import ValidationError

from odrm.api.schemas import PredictRequest, TeaAssumptions, TeaRequest
from odrm.data.schema import BOUNDS, ENUMS

_TOP_LEVEL = ("conditions", "assumptions")
_CONDITION_FIELDS = tuple(PredictRequest.model_fields)
_ASSUMPTION_FIELDS = tuple(TeaAssumptions.model_fields)
_CONDITION_OPTIONAL = ("catalyst_loading_wt_pct", "n2_dilution_mol_pct")
_ASSUMPTION_REQUIRED = (
    "ch4_feed_kmol_per_h",
    "natural_gas_price_usd_per_mmbtu",
    "syngas_price_usd_per_kmol",
    "carbon_credit_price_usd_per_tonne_co2e",
    "capex_usd",
)
_NUMERIC_CONDITIONS = tuple(field for field in _CONDITION_FIELDS if field != "catalyst")
_CATALYSTS = ENUMS["catalyst"]


def _extract_bounds() -> dict[str, tuple[float | None, bool, float | None, bool]]:
    bounds: dict[str, tuple[float | None, bool, float | None, bool]] = {}
    for name, field in TeaAssumptions.model_fields.items():
        lower: float | None = None
        lower_exclusive = False
        upper: float | None = None
        upper_exclusive = False
        for constraint in field.metadata:
            if (value := getattr(constraint, "gt", None)) is not None:
                lower, lower_exclusive = float(value), True
            elif (value := getattr(constraint, "ge", None)) is not None:
                lower, lower_exclusive = float(value), False
            if (value := getattr(constraint, "lt", None)) is not None:
                upper, upper_exclusive = float(value), True
            elif (value := getattr(constraint, "le", None)) is not None:
                upper, upper_exclusive = float(value), False
        bounds[name] = (lower, lower_exclusive, upper, upper_exclusive)
    return bounds


_ASSUMPTION_BOUNDS = _extract_bounds()


class GuardrailViolation(ValueError):
    """A structured, user-correctable rejection raised before the TEA call."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        value: float | str | None = None,
        minimum: float | None = None,
        maximum: float | None = None,
        missing_fields: Sequence[str] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.value = value
        self.minimum = minimum
        self.maximum = maximum
        self.missing_fields = tuple(missing_fields)

    def to_detail(self, request_id: str) -> dict[str, Any]:
        detail: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "value": self.value,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "request_id": request_id,
        }
        if self.missing_fields:
            detail["missing_fields"] = list(self.missing_fields)
        return detail


def _reject(
    code: str,
    message: str,
    *,
    field: str | None = None,
    value: float | str | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    missing_fields: Sequence[str] = (),
) -> NoReturn:
    raise GuardrailViolation(
        code,
        message,
        field=field,
        value=value,
        minimum=minimum,
        maximum=maximum,
        missing_fields=missing_fields,
    )


def _invalid(field: str | None, message: str) -> NoReturn:
    _reject("INVALID_ARGUMENTS", message, field=field)


def _missing(paths: Sequence[str]) -> NoReturn:
    joined = ", ".join(paths)
    _reject(
        "MISSING_ARGUMENTS",
        f"Missing required fields: {joined}.",
        field=paths[0] if paths else None,
        missing_fields=paths,
    )


def _check_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _invalid(field, f"{field} must be an object.")
    return value


def _numeric_value(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _invalid(field, f"{field} must be a finite number.")
    try:
        numeric = float(value)
    except (OverflowError, ValueError):
        _invalid(field, f"{field} must be a finite number.")
    if not math.isfinite(numeric):
        _invalid(field, f"{field} must be a finite number.")
    return numeric


def _check_bounds(
    field: str,
    value: float,
    low: float,
    high: float,
) -> None:
    if value < low or value > high:
        _reject(
            "BOUNDS_VIOLATION",
            f"{field} must be between {low:g} and {high:g}.",
            field=field,
            value=value,
            minimum=low,
            maximum=high,
        )


def _check_assumption_bounds(name: str, value: float) -> None:
    field = f"assumptions.{name}"
    low, low_exclusive, high, high_exclusive = _ASSUMPTION_BOUNDS[name]
    below = low is not None and (value <= low if low_exclusive else value < low)
    above = high is not None and (value >= high if high_exclusive else value > high)
    if below or above:
        _reject(
            "BOUNDS_VIOLATION",
            f"{field} is outside its allowed range.",
            field=field,
            value=value,
            minimum=low,
            maximum=high,
        )


def validate_tea_request(payload: Any) -> TeaRequest:
    body = _check_mapping(payload, "body")
    extras = sorted(set(body) - set(_TOP_LEVEL))
    if extras:
        _invalid(extras[0], f"Unexpected field: {extras[0]}.")
    missing_top = [name for name in _TOP_LEVEL if name not in body]
    if missing_top:
        _missing(missing_top)

    conditions = _check_mapping(body["conditions"], "conditions")
    assumptions = _check_mapping(body["assumptions"], "assumptions")

    condition_extras = sorted(set(conditions) - set(_CONDITION_FIELDS))
    if condition_extras:
        _invalid(
            f"conditions.{condition_extras[0]}",
            f"Unexpected field: conditions.{condition_extras[0]}.",
        )
    assumption_extras = sorted(set(assumptions) - set(_ASSUMPTION_FIELDS))
    if assumption_extras:
        _invalid(
            f"assumptions.{assumption_extras[0]}",
            f"Unexpected field: assumptions.{assumption_extras[0]}.",
        )

    missing = [
        *(f"conditions.{name}" for name in _CONDITION_FIELDS if name not in conditions),
        *(f"assumptions.{name}" for name in _ASSUMPTION_REQUIRED if name not in assumptions),
    ]
    if missing:
        _missing(missing)

    for name in _NUMERIC_CONDITIONS:
        raw = conditions[name]
        if raw is None and name in _CONDITION_OPTIONAL:
            continue
        numeric = _numeric_value(raw, f"conditions.{name}")
        if name in BOUNDS:
            low, high = BOUNDS[name]
            _check_bounds(f"conditions.{name}", numeric, low, high)

    catalyst = conditions["catalyst"]
    if not isinstance(catalyst, str):
        _invalid("conditions.catalyst", "conditions.catalyst must be a string.")
    if catalyst not in _CATALYSTS:
        _reject(
            "UNKNOWN_CATALYST",
            f"conditions.catalyst must be one of: {', '.join(_CATALYSTS)}.",
            field="conditions.catalyst",
            value=catalyst,
        )

    for name in _ASSUMPTION_FIELDS:
        if name not in assumptions:
            continue
        numeric = _numeric_value(assumptions[name], f"assumptions.{name}")
        _check_assumption_bounds(name, numeric)

    try:
        return TeaRequest.model_validate(body)
    except ValidationError as exc:
        error = exc.errors()[0]
        field = ".".join(str(part) for part in error["loc"])
        if error["type"] == "missing":
            _missing((field,))
        _invalid(field, f"{field} is invalid.")

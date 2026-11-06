from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from xml.sax.saxutils import escape

from odrm.api.schemas import TeaRequest, TeaResponse

SCHEMA_VERSION = "esg-report/v1"
CURRENCY = "USD"

WARNING_MESSAGES: dict[str, str] = {
    "carbon_credit_not_included": (
        "Carbon-credit revenue is excluded because the CO2 utilization fraction is zero."
    ),
    "negative_annual_cash_flow": (
        "Annual net cash flow is negative under the supplied assumptions."
    ),
    "syngas_yield_out_of_envelope": (
        "Predicted syngas yield falls outside the surrogate model's validated range."
    ),
    "zero_syngas_price": "Syngas price is zero, so syngas revenue is zero.",
    "zero_carbon_price": "Carbon-credit price is zero, so carbon-credit revenue is zero.",
}


@dataclass(frozen=True)
class ReportWarning:
    code: str
    message: str


@dataclass(frozen=True)
class ReportData:
    report_id: str
    generated_at: str
    schema_version: str
    request: TeaRequest
    response: TeaResponse
    warnings: tuple[ReportWarning, ...]
    canonical_payload: str
    sha256: str


def format_optional(value: float | str | None) -> str:
    if value is None:
        return "Not provided"
    if isinstance(value, float):
        return f"{value:g}"
    return value


def safe_report_text(value: str, *, max_length: int = 120) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    collapsed = " ".join(normalized.split())
    return escape(collapsed[:max_length])


def _format_generated_at(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _warning(code: str) -> ReportWarning:
    return ReportWarning(code=code, message=WARNING_MESSAGES.get(code, code))


def build_report_data(
    request: TeaRequest,
    response: TeaResponse,
    *,
    report_id: str,
    generated_at: datetime,
) -> ReportData:
    timestamp = _format_generated_at(generated_at)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "report_id": report_id,
        "generated_at": timestamp,
        "request": request.model_dump(mode="json"),
        "response": response.model_dump(mode="json"),
    }
    canonical_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    return ReportData(
        report_id=report_id,
        generated_at=timestamp,
        schema_version=SCHEMA_VERSION,
        request=request,
        response=response,
        warnings=tuple(_warning(code) for code in response.warnings),
        canonical_payload=canonical_payload,
        sha256=digest,
    )

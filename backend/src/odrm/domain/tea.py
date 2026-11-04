from __future__ import annotations

import math
from dataclasses import dataclass

CH4_LHV_MMBTU_PER_KMOL = 0.7603
CO2_MOLAR_MASS_KG_PER_KMOL = 44.01
MOLAR_VOLUME_NM3_PER_KMOL = 22.414

DEFAULT_CO2_UTILIZATION_FRACTION = 0.0
DEFAULT_OPEX_PCT_OF_CAPEX_PER_YEAR = 5.0
DEFAULT_OPERATING_HOURS_PER_DAY = 24.0
DEFAULT_OPERATING_DAYS_PER_YEAR = 330.0


class TeaInputError(ValueError):
    """Raised when a TEA assumption or prediction input is invalid."""


class TeaCalculationError(ValueError):
    """Raised when a TEA calculation produces a non-finite result."""


@dataclass(frozen=True)
class TeaInputs:
    syngas_yield_mol_per_mol_ch4: float
    ch4_feed_kmol_per_h: float
    co2_ch4_ratio: float
    natural_gas_price_usd_per_mmbtu: float
    syngas_price_usd_per_kmol: float
    carbon_credit_price_usd_per_tonne_co2e: float
    capex_usd: float
    co2_utilization_fraction: float = DEFAULT_CO2_UTILIZATION_FRACTION
    opex_pct_of_capex_per_year: float = DEFAULT_OPEX_PCT_OF_CAPEX_PER_YEAR
    operating_hours_per_day: float = DEFAULT_OPERATING_HOURS_PER_DAY
    operating_days_per_year: float = DEFAULT_OPERATING_DAYS_PER_YEAR

    def __post_init__(self) -> None:
        _validate_inputs(self)


@dataclass(frozen=True)
class TeaResult:
    syngas_kmol_per_day: float
    syngas_nm3_per_day: float
    syngas_revenue_usd_per_day: float
    co2_consumed_tonnes_per_day: float
    carbon_credit_value_usd_per_day: float
    total_revenue_usd_per_day: float
    feed_cost_usd_per_day: float
    opex_usd_per_day: float
    net_cash_flow_usd_per_day: float
    annual_net_cash_flow_usd: float
    roi_pct: float
    payback_years: float | None
    warnings: tuple[str, ...]


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise TeaInputError(f"{name} must be finite; got {value!r}")


def _require_at_least(name: str, value: float, minimum: float, inclusive: bool = True) -> None:
    if value < minimum or (not inclusive and value == minimum):
        comparator = ">=" if inclusive else ">"
        raise TeaInputError(f"{name} must be {comparator} {minimum:g}; got {value!r}")


def _require_at_most(name: str, value: float, maximum: float) -> None:
    if value > maximum:
        raise TeaInputError(f"{name} must be <= {maximum:g}; got {value!r}")


def _validate_inputs(inputs: TeaInputs) -> None:
    fields = (
        "syngas_yield_mol_per_mol_ch4",
        "ch4_feed_kmol_per_h",
        "co2_ch4_ratio",
        "natural_gas_price_usd_per_mmbtu",
        "syngas_price_usd_per_kmol",
        "carbon_credit_price_usd_per_tonne_co2e",
        "capex_usd",
        "co2_utilization_fraction",
        "opex_pct_of_capex_per_year",
        "operating_hours_per_day",
        "operating_days_per_year",
    )
    for name in fields:
        _require_finite(name, getattr(inputs, name))

    _require_at_least("syngas_yield_mol_per_mol_ch4", inputs.syngas_yield_mol_per_mol_ch4, 0.0)
    _require_at_least("ch4_feed_kmol_per_h", inputs.ch4_feed_kmol_per_h, 0.0, inclusive=False)
    _require_at_most("ch4_feed_kmol_per_h", inputs.ch4_feed_kmol_per_h, 1_000_000.0)
    _require_at_least("co2_ch4_ratio", inputs.co2_ch4_ratio, 0.0)
    _require_at_most("co2_ch4_ratio", inputs.co2_ch4_ratio, 1.5)
    _require_at_least(
        "natural_gas_price_usd_per_mmbtu", inputs.natural_gas_price_usd_per_mmbtu, 0.0
    )
    _require_at_most(
        "natural_gas_price_usd_per_mmbtu", inputs.natural_gas_price_usd_per_mmbtu, 1_000.0
    )
    _require_at_least("syngas_price_usd_per_kmol", inputs.syngas_price_usd_per_kmol, 0.0)
    _require_at_most("syngas_price_usd_per_kmol", inputs.syngas_price_usd_per_kmol, 1_000_000.0)
    _require_at_least(
        "carbon_credit_price_usd_per_tonne_co2e",
        inputs.carbon_credit_price_usd_per_tonne_co2e,
        0.0,
    )
    _require_at_most(
        "carbon_credit_price_usd_per_tonne_co2e",
        inputs.carbon_credit_price_usd_per_tonne_co2e,
        100_000.0,
    )
    _require_at_least("co2_utilization_fraction", inputs.co2_utilization_fraction, 0.0)
    _require_at_most("co2_utilization_fraction", inputs.co2_utilization_fraction, 1.0)
    _require_at_least("capex_usd", inputs.capex_usd, 0.0, inclusive=False)
    _require_at_most("capex_usd", inputs.capex_usd, 1e12)
    _require_at_least("opex_pct_of_capex_per_year", inputs.opex_pct_of_capex_per_year, 0.0)
    _require_at_most("opex_pct_of_capex_per_year", inputs.opex_pct_of_capex_per_year, 100.0)
    _require_at_least(
        "operating_hours_per_day", inputs.operating_hours_per_day, 0.0, inclusive=False
    )
    _require_at_most("operating_hours_per_day", inputs.operating_hours_per_day, 24.0)
    _require_at_least(
        "operating_days_per_year", inputs.operating_days_per_year, 0.0, inclusive=False
    )
    _require_at_most("operating_days_per_year", inputs.operating_days_per_year, 365.0)


def _finite_result(name: str, value: float) -> float:
    if not math.isfinite(value):
        raise TeaCalculationError(f"non-finite TEA result for {name}")
    return value


def calculate_tea(inputs: TeaInputs) -> TeaResult:
    syngas_kmol_per_day = _finite_result(
        "syngas_kmol_per_day",
        inputs.ch4_feed_kmol_per_h
        * inputs.syngas_yield_mol_per_mol_ch4
        * inputs.operating_hours_per_day,
    )
    syngas_nm3_per_day = _finite_result(
        "syngas_nm3_per_day", syngas_kmol_per_day * MOLAR_VOLUME_NM3_PER_KMOL
    )
    syngas_revenue_usd_per_day = _finite_result(
        "syngas_revenue_usd_per_day",
        syngas_kmol_per_day * inputs.syngas_price_usd_per_kmol,
    )

    co2_consumed_kmol_per_h = _finite_result(
        "co2_consumed_kmol_per_h",
        inputs.ch4_feed_kmol_per_h * inputs.co2_ch4_ratio * inputs.co2_utilization_fraction,
    )
    co2_consumed_tonnes_per_day = _finite_result(
        "co2_consumed_tonnes_per_day",
        co2_consumed_kmol_per_h
        * inputs.operating_hours_per_day
        * CO2_MOLAR_MASS_KG_PER_KMOL
        / 1000.0,
    )
    carbon_credit_value_usd_per_day = _finite_result(
        "carbon_credit_value_usd_per_day",
        co2_consumed_tonnes_per_day * inputs.carbon_credit_price_usd_per_tonne_co2e,
    )

    feed_cost_usd_per_day = _finite_result(
        "feed_cost_usd_per_day",
        inputs.ch4_feed_kmol_per_h
        * inputs.operating_hours_per_day
        * inputs.natural_gas_price_usd_per_mmbtu
        * CH4_LHV_MMBTU_PER_KMOL,
    )
    opex_usd_per_day = _finite_result(
        "opex_usd_per_day",
        inputs.capex_usd
        * (inputs.opex_pct_of_capex_per_year / 100.0)
        / inputs.operating_days_per_year,
    )

    total_revenue_usd_per_day = _finite_result(
        "total_revenue_usd_per_day",
        syngas_revenue_usd_per_day + carbon_credit_value_usd_per_day,
    )
    net_cash_flow_usd_per_day = _finite_result(
        "net_cash_flow_usd_per_day",
        total_revenue_usd_per_day - feed_cost_usd_per_day - opex_usd_per_day,
    )
    annual_net_cash_flow_usd = _finite_result(
        "annual_net_cash_flow_usd",
        net_cash_flow_usd_per_day * inputs.operating_days_per_year,
    )
    roi_pct = _finite_result("roi_pct", annual_net_cash_flow_usd / inputs.capex_usd * 100.0)

    payback_years = (
        _finite_result("payback_years", inputs.capex_usd / annual_net_cash_flow_usd)
        if annual_net_cash_flow_usd > 0
        else None
    )

    warnings: list[str] = []
    if (
        inputs.co2_utilization_fraction == 0.0
        and inputs.carbon_credit_price_usd_per_tonne_co2e > 0.0
    ):
        warnings.append("carbon_credit_not_included")
    if annual_net_cash_flow_usd <= 0.0:
        warnings.append("negative_annual_cash_flow")
    if inputs.syngas_yield_mol_per_mol_ch4 > 8.0:
        warnings.append("syngas_yield_out_of_envelope")
    if inputs.syngas_price_usd_per_kmol == 0.0:
        warnings.append("zero_syngas_price")
    if inputs.carbon_credit_price_usd_per_tonne_co2e == 0.0:
        warnings.append("zero_carbon_price")

    return TeaResult(
        syngas_kmol_per_day=syngas_kmol_per_day,
        syngas_nm3_per_day=syngas_nm3_per_day,
        syngas_revenue_usd_per_day=syngas_revenue_usd_per_day,
        co2_consumed_tonnes_per_day=co2_consumed_tonnes_per_day,
        carbon_credit_value_usd_per_day=carbon_credit_value_usd_per_day,
        total_revenue_usd_per_day=total_revenue_usd_per_day,
        feed_cost_usd_per_day=feed_cost_usd_per_day,
        opex_usd_per_day=opex_usd_per_day,
        net_cash_flow_usd_per_day=net_cash_flow_usd_per_day,
        annual_net_cash_flow_usd=annual_net_cash_flow_usd,
        roi_pct=roi_pct,
        payback_years=payback_years,
        warnings=tuple(warnings),
    )

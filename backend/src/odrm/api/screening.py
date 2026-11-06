from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odrm.api.schemas import TeaFinancials, TeaRequest, TeaResponse
from odrm.domain.tea import TeaInputs, TeaResult, calculate_tea
from odrm.services.prediction import predict_surrogates


def tea_financials(result: TeaResult) -> TeaFinancials:
    return TeaFinancials(
        syngas_kmol_per_day=round(result.syngas_kmol_per_day, 2),
        syngas_nm3_per_day=round(result.syngas_nm3_per_day, 2),
        syngas_revenue_usd_per_day=round(result.syngas_revenue_usd_per_day, 2),
        co2_consumed_tonnes_per_day=round(result.co2_consumed_tonnes_per_day, 4),
        carbon_credit_value_usd_per_day=round(result.carbon_credit_value_usd_per_day, 2),
        total_revenue_usd_per_day=round(result.total_revenue_usd_per_day, 2),
        feed_cost_usd_per_day=round(result.feed_cost_usd_per_day, 2),
        opex_usd_per_day=round(result.opex_usd_per_day, 2),
        net_cash_flow_usd_per_day=round(result.net_cash_flow_usd_per_day, 2),
        annual_net_cash_flow_usd=round(result.annual_net_cash_flow_usd, 2),
        roi_pct=round(result.roi_pct, 2),
        payback_years=(None if result.payback_years is None else round(result.payback_years, 4)),
    )


def run_screening(
    request: TeaRequest,
    models: Mapping[str, tuple[Any, dict[str, Any]]],
) -> TeaResponse:
    assumptions = request.assumptions
    predictions, versions = predict_surrogates(models, request.conditions.model_dump())
    inputs = TeaInputs(
        syngas_yield_mol_per_mol_ch4=predictions["syngas_yield_mol_per_mol_ch4"],
        ch4_feed_kmol_per_h=assumptions.ch4_feed_kmol_per_h,
        co2_ch4_ratio=request.conditions.co2_ch4_ratio,
        natural_gas_price_usd_per_mmbtu=assumptions.natural_gas_price_usd_per_mmbtu,
        syngas_price_usd_per_kmol=assumptions.syngas_price_usd_per_kmol,
        carbon_credit_price_usd_per_tonne_co2e=(
            assumptions.carbon_credit_price_usd_per_tonne_co2e
        ),
        capex_usd=assumptions.capex_usd,
        co2_utilization_fraction=assumptions.co2_utilization_fraction,
        opex_pct_of_capex_per_year=assumptions.opex_pct_of_capex_per_year,
        operating_hours_per_day=assumptions.operating_hours_per_day,
        operating_days_per_year=assumptions.operating_days_per_year,
    )
    result = calculate_tea(inputs)

    return TeaResponse(
        predictions=predictions,
        model_versions=versions,
        financials=tea_financials(result),
        warnings=list(result.warnings),
    )

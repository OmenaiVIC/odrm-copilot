from fastapi import APIRouter, HTTPException, Request

from odrm.api.schemas import (
    MarketPricesResponse,
    PredictRequest,
    PredictResponse,
    TeaFinancials,
    TeaRequest,
    TeaResponse,
)
from odrm.domain.tea import (
    TeaCalculationError,
    TeaInputError,
    TeaInputs,
    TeaResult,
    calculate_tea,
)
from odrm.ml.features import TARGETS
from odrm.services.market_data import MarketDataError, MarketDataService
from odrm.services.prediction import (
    ModelUnavailableError,
    PredictionError,
    predict_surrogates,
)

router = APIRouter()
market_router = APIRouter()


def _tea_financials(result: TeaResult) -> TeaFinancials:
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


@router.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest, req: Request) -> PredictResponse:
    try:
        predictions, versions = predict_surrogates(req.app.state.models, request.model_dump())
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PredictionError as exc:
        raise HTTPException(status_code=500, detail="Model prediction failed.") from exc

    return PredictResponse(predictions=predictions, model_version=versions[TARGETS[-1]])


@router.post("/tea", response_model=TeaResponse)
def tea(request: TeaRequest, req: Request) -> TeaResponse:
    assumptions = request.assumptions
    try:
        predictions, versions = predict_surrogates(
            req.app.state.models, request.conditions.model_dump()
        )
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
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PredictionError as exc:
        raise HTTPException(status_code=500, detail="Model prediction failed.") from exc
    except TeaInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TeaCalculationError as exc:
        raise HTTPException(status_code=500, detail="TEA calculation failed.") from exc

    return TeaResponse(
        predictions=predictions,
        model_versions=versions,
        financials=_tea_financials(result),
        warnings=list(result.warnings),
    )


@market_router.get("/market-prices", response_model=MarketPricesResponse)
def market_prices(req: Request) -> MarketPricesResponse:
    service: MarketDataService = req.app.state.market_data
    try:
        quote, cached = service.get_prices()
    except MarketDataError as exc:
        raise HTTPException(status_code=503, detail="Market data unavailable.") from exc

    return MarketPricesResponse(
        natural_gas_price_usd_per_mmbtu=quote.natural_gas_price_usd_per_mmbtu,
        syngas_price_usd_per_kmol=quote.syngas_price_usd_per_kmol,
        carbon_credit_price_usd_per_tonne_co2e=quote.carbon_credit_price_usd_per_tonne_co2e,
        currency="USD",
        source=quote.source,
        is_mock=quote.is_mock,
        as_of=quote.as_of,
        cached=cached,
        cache_ttl_seconds=int(service.ttl_seconds),
    )

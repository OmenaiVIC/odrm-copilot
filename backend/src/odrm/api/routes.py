from fastapi import APIRouter, HTTPException, Request

from odrm.api.schemas import (
    MarketPricesResponse,
    PredictRequest,
    PredictResponse,
    TeaRequest,
    TeaResponse,
)
from odrm.api.screening import run_screening
from odrm.domain.tea import TeaCalculationError, TeaInputError
from odrm.ml.features import TARGETS
from odrm.services.market_data import MarketDataError, MarketDataService
from odrm.services.prediction import (
    ModelUnavailableError,
    PredictionError,
    predict_surrogates,
)

router = APIRouter()
market_router = APIRouter()


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
    try:
        return run_screening(request, req.app.state.models)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PredictionError as exc:
        raise HTTPException(status_code=500, detail="Model prediction failed.") from exc
    except TeaInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TeaCalculationError as exc:
        raise HTTPException(status_code=500, detail="TEA calculation failed.") from exc


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

from fastapi import APIRouter, HTTPException, Request

from odrm.api.schemas import PredictRequest, PredictResponse
from odrm.ml.features import TARGETS
from odrm.services.prediction import (
    ModelUnavailableError,
    PredictionError,
    predict_surrogates,
)

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest, req: Request) -> PredictResponse:
    try:
        predictions, versions = predict_surrogates(req.app.state.models, request.model_dump())
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PredictionError as exc:
        raise HTTPException(status_code=500, detail="Model prediction failed.") from exc

    return PredictResponse(predictions=predictions, model_version=versions[TARGETS[-1]])

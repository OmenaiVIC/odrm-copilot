import pandas as pd
from fastapi import APIRouter, HTTPException, Request

from odrm.api.schemas import PredictRequest, PredictResponse
from odrm.ml.features import TARGETS, build_feature_frame

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest, req: Request) -> PredictResponse:
    models = req.app.state.models
    if not models or len(models) < len(TARGETS):
        raise HTTPException(
            status_code=503,
            detail="Model unavailable. The surrogate models are not loaded on the server.",
        )

    input_df = pd.DataFrame([request.model_dump()])
    X = build_feature_frame(input_df)

    predictions = {}
    version = "unknown"

    for target in TARGETS:
        model, metadata = models[target]
        version = metadata["model_version"]
        pred = model.predict(X)[0]
        predictions[target] = float(pred)

    return PredictResponse(predictions=predictions, model_version=version)

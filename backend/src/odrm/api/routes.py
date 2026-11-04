from fastapi import APIRouter, HTTPException, Request
import pandas as pd

from odrm.api.schemas import PredictRequest, PredictResponse
from odrm.ml.features import build_feature_frame, TARGETS

router = APIRouter()

@router.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest, req: Request):
    # 1. Check if models are loaded
    models = req.app.state.models
    if not models or len(models) < len(TARGETS):
        raise HTTPException(
            status_code=503, 
            detail="Model unavailable. The surrogate models are not loaded on the server."
        )
        
    # 2. Convert request to DataFrame
    input_df = pd.DataFrame([request.model_dump()])
    X = build_feature_frame(input_df)
    
    predictions = {}
    version = "unknown"
    
    # 3. Predict from memory
    for target in TARGETS:
        model, metadata = models[target]
        version = metadata["model_version"]
        pred = model.predict(X)[0]
        predictions[target] = float(pred)
        
    return PredictResponse(
        predictions=predictions,
        model_version=version
    )
from fastapi import APIRouter, HTTPException
from pathlib import Path
import pandas as pd

from odrm.api.schemas import PredictRequest, PredictResponse
from odrm.ml.registry import load_model, ModelNotFoundError
from odrm.ml.features import build_feature_frame, TARGETS

router = APIRouter()

# We point to the model directory at the project root
MODEL_ROOT = Path("models/odrm")

@router.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    # 1. Convert request to a single-row DataFrame
    input_df = pd.DataFrame([request.model_dump()])
    
    predictions = {}
    version = "unknown"
    
    try:
        # 2. Load models and predict
        for target in TARGETS:
            model, metadata = load_model(target=target, root=MODEL_ROOT)
            version = metadata["model_version"]
            
            # Build the features using our strict pipeline
            X = build_feature_frame(input_df)
            
            # Predict
            pred = model.predict(X)[0]
            predictions[target] = float(pred)
            
    except ModelNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
        
    return PredictResponse(
        predictions=predictions,
        model_version=version
    )
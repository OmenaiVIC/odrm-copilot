import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from odrm.core.config import Settings
from odrm.api.routes import router as predict_router
from odrm.ml.registry import load_model, ModelNotFoundError
from odrm.ml.features import TARGETS

logger = logging.getLogger(__name__)

def create_app(settings: Optional[Settings] = None) -> FastAPI:
    if settings is None:
        settings = Settings(env="dev") 

    app = FastAPI(title="ODRM-Copilot API")
    
    # FIX: Attach settings to state for legacy tests
    app.state.settings = settings
    
    origins = getattr(settings, "cors_origins", "*")
    if isinstance(origins, str):
        origins = [o.strip() for o in origins.split(",")]
        
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.state.models = {}
    
    base_model_dir = Path(getattr(settings, "model_dir", "models"))
    if (base_model_dir / "odrm").is_dir():
        model_root = base_model_dir / "odrm"
    else:
        model_root = base_model_dir
        
    for target in TARGETS:
        try:
            model, meta = load_model(target, root=model_root)
            app.state.models[target] = (model, meta)
            logger.info(f"Loaded model {target} version {meta['model_version']}")
        except ModelNotFoundError:
            logger.warning(f"Model {target} not found in {model_root}. API will return 503.")

    app.include_router(predict_router, prefix="/api/v1", tags=["predict"])
    
    @app.get("/health")
    def health():
        return {"status": "ok", "env": getattr(settings, "env", "test")}
        
    return app

app = create_app()

def main() -> None:
    import uvicorn
    uvicorn.run("odrm.main:app", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
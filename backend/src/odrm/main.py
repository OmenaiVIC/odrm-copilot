import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from odrm.api.routes import market_router
from odrm.api.routes import router as predict_router
from odrm.core.config import Settings
from odrm.ml.features import TARGETS
from odrm.ml.registry import ModelNotFoundError, load_model
from odrm.services.market_data import MarketDataService, MockMarketPriceProvider

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings(env="dev")

    app = FastAPI(title="ODRM-Copilot API")
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
    app.state.market_data = MarketDataService(
        provider=MockMarketPriceProvider(),
        ttl_seconds=settings.market_data_ttl_seconds,
    )

    base_model_dir = Path(getattr(settings, "model_dir", "models"))
    model_root = base_model_dir / "odrm" if (base_model_dir / "odrm").is_dir() else base_model_dir

    for target in TARGETS:
        try:
            model, meta = load_model(target, root=model_root)
            app.state.models[target] = (model, meta)
            logger.info(f"Loaded model {target} version {meta['model_version']}")
        except ModelNotFoundError:
            logger.warning(f"Model {target} not found in {model_root}. API will return 503.")

    app.include_router(predict_router, prefix="/api/v1", tags=["predict"])
    app.include_router(market_router, prefix="/api/v1", tags=["market"])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "env": getattr(settings, "env", "test")}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("odrm.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from odrm.agents.orchestrator import AgentService
from odrm.agents.providers import build_chat_model
from odrm.agents.tea_client import InProcessTeaClient
from odrm.api.chat import router as chat_router
from odrm.api.report import EXPOSED_HEADERS
from odrm.api.report import router as report_router
from odrm.api.routes import market_router
from odrm.api.routes import router as predict_router
from odrm.auth.passwords import PasswordHasher
from odrm.auth.repository import SqlAlchemyUserRepository, UserRepository
from odrm.auth.router import router as auth_router
from odrm.auth.service import AuthService
from odrm.auth.tokens import TokenService
from odrm.core.config import Settings
from odrm.db import create_session_factory
from odrm.ml.features import TARGETS
from odrm.ml.registry import ModelNotFoundError, load_model
from odrm.services.market_data import MarketDataService, MockMarketPriceProvider

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    agent_service: AgentService | None = None,
    user_repository: UserRepository | None = None,
) -> FastAPI:
    if settings is None:
        settings = Settings(env="dev")

    app = FastAPI(title="ODRM-Copilot API")
    app.state.settings = settings
    repository = user_repository or SqlAlchemyUserRepository(
        create_session_factory(settings.database_url)
    )
    app.state.user_repository = repository
    token_service = TokenService(settings)
    app.state.token_service = token_service
    app.state.auth_service = AuthService(repository, PasswordHasher(), token_service)

    origins = getattr(settings, "cors_origins", "*")
    if isinstance(origins, str):
        origins = [o.strip() for o in origins.split(",")]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=list(EXPOSED_HEADERS),
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

    app.state.agent_service = agent_service or AgentService(
        tea_client=InProcessTeaClient(app.state.models),
        model_factory=lambda: build_chat_model(settings),
    )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(predict_router, prefix="/api/v1", tags=["predict"])
    app.include_router(market_router, prefix="/api/v1", tags=["market"])
    app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
    app.include_router(report_router, prefix="/api/v1", tags=["report"])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "env": getattr(settings, "env", "test")}

    @app.get("/ready")
    def ready(request: Request) -> dict[str, str]:
        repository: UserRepository = request.app.state.user_repository
        try:
            repository.ping()
        except Exception as exc:
            logger.warning("Database readiness check failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=503,
                detail="Database is not ready.",
            ) from exc
        return {"status": "ready"}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("odrm.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

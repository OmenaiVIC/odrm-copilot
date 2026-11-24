import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from odrm.agents.orchestrator import AgentService
from odrm.agents.providers import build_chat_model
from odrm.agents.tea_client import InProcessTeaClient
from odrm.api.chat import router as chat_router
from odrm.api.evidence import router as evidence_router
from odrm.api.report import EXPOSED_HEADERS
from odrm.api.report import router as report_router
from odrm.api.routes import market_router
from odrm.api.routes import router as predict_router
from odrm.api.whitelist import router as whitelist_router
from odrm.auth.passwords import PasswordHasher
from odrm.auth.repository import SqlAlchemyUserRepository, UserRepository
from odrm.auth.router import router as auth_router
from odrm.auth.service import AuthService
from odrm.auth.tokens import TokenService
from odrm.core.config import Settings
from odrm.db import create_session_factory
from odrm.evidence.repository import (
    EvidenceRepository,
    SqlAlchemyEvidenceRepository,
)
from odrm.evidence.service import EvidenceService, merkle_root
from odrm.ml.features import TARGETS
from odrm.ml.registry import ModelNotFoundError, load_model
from odrm.services.market_data import MarketDataService, MockMarketPriceProvider
from odrm.whitelist.repository import (
    SqlAlchemyWhitelistRepository,
    WhitelistRepository,
)
from odrm.whitelist.service import WhitelistService

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    agent_service: AgentService | None = None,
    user_repository: UserRepository | None = None,
    whitelist_repository: WhitelistRepository | None = None,
    evidence_repository: EvidenceRepository | None = None,
) -> FastAPI:
    if settings is None:
        settings = Settings(env="dev")

    app = FastAPI(title="ODRM-Copilot API")
    app.state.settings = settings
    
    session_factory = create_session_factory(settings.database_url)
    
    repository = user_repository or SqlAlchemyUserRepository(session_factory)
    app.state.user_repository = repository
    
    whitelist_store: WhitelistRepository = (
        whitelist_repository or SqlAlchemyWhitelistRepository(session_factory)
    )
    app.state.whitelist_repository = whitelist_store
    app.state.whitelist_service = WhitelistService(whitelist_store)

    evidence_store: EvidenceRepository = (
        evidence_repository
        or SqlAlchemyEvidenceRepository(session_factory, root_builder=merkle_root)
    )
    app.state.evidence_repository = evidence_store
    app.state.evidence_service = EvidenceService(evidence_store)

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
        history_max_messages=settings.chat_history_max_messages,
        history_max_chars=settings.chat_history_max_chars,
    )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(whitelist_router, prefix="/api/v1")
    app.include_router(predict_router, prefix="/api/v1", tags=["predict"])
    app.include_router(market_router, prefix="/api/v1", tags=["market"])
    app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
    app.include_router(report_router, prefix="/api/v1", tags=["report"])
    app.include_router(evidence_router, prefix="/api/v1", tags=["evidence"])

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
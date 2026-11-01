from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from odrm.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()

    app = FastAPI(
        title="ODRM-Copilot API",
        version="0.1.0",
        description="Surrogate process modelling and optimization API for flare gas valorization.",
    )
    app.state.settings = cfg

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "env": cfg.env}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("odrm.main:app", host="0.0.0.0", port=8000)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from odrm.api.routes import router as predict_router

def create_app() -> FastAPI:
    app = FastAPI(title="ODRM Copilot")
    
    # Simplified CORS for local testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # We can lock this down later
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount the prediction API
    app.include_router(predict_router, prefix="/api/v1", tags=["predict"])
    
    @app.get("/health")
    def health():
        return {"status": "ok"}
        
    return app

app = create_app()

def main() -> None:
    import uvicorn
    uvicorn.run("odrm.main:app", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
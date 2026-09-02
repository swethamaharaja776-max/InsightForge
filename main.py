from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config
from .database import Base, engine
from . import db_models  # noqa: F401  (ensures models are registered)
from .routers import datasets, history, reports

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="InsightForge API",
    description="AI-Powered Data Intelligence Platform - Backend API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


app.include_router(datasets.router)
app.include_router(history.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {
        "name": "InsightForge API",
        "status": "online",
        "docs": "/docs",
        "ai_provider": config.AI_PROVIDER,
    }


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

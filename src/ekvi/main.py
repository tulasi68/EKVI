"""EKVI FastAPI application — pre-gate prototype entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ekvi import __version__
from ekvi.api import projects, ingestion, assessment, disposition
from ekvi.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.storage_backend == "local":
        from pathlib import Path
        Path(settings.storage_local_path).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="EKVI",
    description=(
        "Engineering Knowledge & Verification Intelligence — pre-gate prototype. "
        "Document-first verification adequacy assessment with evidence spans, "
        "obligation model, and disposition logging."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["ingestion"])
app.include_router(assessment.router, prefix="/api/v1/assessment", tags=["assessment"])
app.include_router(disposition.router, prefix="/api/v1/disposition", tags=["disposition"])


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "app": get_settings().app_name,
        "env": get_settings().app_env,
    }


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "EKVI prototype API",
        "docs": "/docs",
        "health": "/health",
    }

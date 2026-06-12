"""FIFA 2026 Multi-Agent Intelligence Platform — API entrypoint."""

from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1 import auth, chat, health, matches, predictions, simulation, teams
from app.core.config import get_settings

log = structlog.get_logger()
settings = get_settings()

app = FastAPI(
    title="FIFA 2026 Intelligence Platform",
    description="Multi-agent AI platform for FIFA 2026 World Cup analytics, predictions, and simulation.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Prometheus metrics ─────────────────────────────────────────────────────────

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ── Routers ────────────────────────────────────────────────────────────────────

prefix = settings.api_v1_prefix

app.include_router(health.router, prefix=f"{prefix}/health")
app.include_router(teams.router, prefix=f"{prefix}/teams", tags=["Teams"])
app.include_router(matches.router, prefix=f"{prefix}/matches", tags=["Matches"])
app.include_router(predictions.router, prefix=f"{prefix}/predictions", tags=["Predictions"])
app.include_router(simulation.router, prefix=f"{prefix}/simulation", tags=["Simulation"])
app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["Auth"])
app.include_router(chat.router, prefix=f"{prefix}/chat", tags=["Chat"])


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"message": "FIFA 2026 Intelligence Platform", "docs": "/docs"}

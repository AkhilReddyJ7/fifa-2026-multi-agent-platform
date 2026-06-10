from __future__ import annotations

import asyncio

import redis.asyncio as aioredis
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.schemas.common import HealthResponse

router = APIRouter()
settings = get_settings()

VERSION = "1.0.0"


async def _check_db() -> str:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


async def _check_redis() -> str:
    try:
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


async def _check_chroma() -> str:
    try:
        import chromadb

        client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        client.heartbeat()
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"error: {exc}"


@router.get("", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    db_status, redis_status, chroma_status = await asyncio.gather(
        _check_db(), _check_redis(), _check_chroma()
    )
    return HealthResponse(
        status="ok",
        version=VERSION,
        environment=settings.app_env,
        db=db_status,
        redis=redis_status,
        chroma=chroma_status,
    )

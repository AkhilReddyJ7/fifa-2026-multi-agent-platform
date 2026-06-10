from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    db: str
    redis: str
    chroma: str


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None

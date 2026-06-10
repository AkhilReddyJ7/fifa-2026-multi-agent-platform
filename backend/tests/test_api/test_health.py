"""Health endpoint tests — service dependency checks are mocked."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    with (
        patch("app.api.v1.health._check_db", new_callable=AsyncMock, return_value="ok"),
        patch("app.api.v1.health._check_redis", new_callable=AsyncMock, return_value="ok"),
        patch("app.api.v1.health._check_chroma", new_callable=AsyncMock, return_value="ok"),
    ):
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["redis"] == "ok"
    assert body["chroma"] == "ok"
    assert "version" in body
    assert "environment" in body


@pytest.mark.asyncio
async def test_health_reports_degraded_services(client: AsyncClient) -> None:
    with (
        patch("app.api.v1.health._check_db", new_callable=AsyncMock, return_value="ok"),
        patch("app.api.v1.health._check_redis", new_callable=AsyncMock, return_value="error: Connection refused"),
        patch("app.api.v1.health._check_chroma", new_callable=AsyncMock, return_value="error: timeout"),
    ):
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert "error" in body["redis"]
    assert "error" in body["chroma"]

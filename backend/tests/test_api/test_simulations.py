"""API tests for simulation persistence (Phase 3B)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# ── Fixtures ──────────────────────────────────────────────────────────────────

MOCK_SIM_STATE = {
    "sim_results": {
        "n_simulations": 100,
        "win_probabilities": {"BRA": 0.20, "ARG": 0.18, "FRA": 0.15},
        "final_probabilities": {"BRA": 0.35, "ARG": 0.30, "FRA": 0.25},
        "semifinal_probabilities": {"BRA": 0.55, "ARG": 0.50, "FRA": 0.45},
        "top_5_favorites": ["BRA", "ARG", "FRA", "ENG", "ESP"],
        "expected_bracket": {"winner": "BRA", "runner_up": "ARG"},
    },
    "response": "Brazil is the favourite to win FIFA 2026.",
    "trace": [],
}


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_simulation_saves_and_returns_id(client: AsyncClient) -> None:
    with patch("app.api.v1.simulation.run_query", new=AsyncMock(return_value=MOCK_SIM_STATE)):
        r = await client.post("/api/v1/simulation", json={"n_simulations": 100})
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert isinstance(body["id"], int)
    assert body["id"] > 0
    assert "run_uuid" in body
    assert len(body["run_uuid"]) > 0
    assert body["n_simulations"] == 100


@pytest.mark.asyncio
async def test_get_simulation_by_run_uuid(client: AsyncClient) -> None:
    with patch("app.api.v1.simulation.run_query", new=AsyncMock(return_value=MOCK_SIM_STATE)):
        post_r = await client.post("/api/v1/simulation", json={"n_simulations": 100})
    assert post_r.status_code == 200
    run_uuid = post_r.json()["run_uuid"]

    get_r = await client.get(f"/api/v1/simulation/{run_uuid}")
    assert get_r.status_code == 200
    body = get_r.json()
    assert body["run_uuid"] == run_uuid
    assert body["n_simulations"] == 100
    assert body["win_probabilities"]["BRA"] == pytest.approx(0.20)
    assert body["top_5_favorites"] == ["BRA", "ARG", "FRA", "ENG", "ESP"]


@pytest.mark.asyncio
async def test_get_simulation_not_found(client: AsyncClient) -> None:
    r = await client.get("/api/v1/simulation/nonexistent-uuid-12345")
    assert r.status_code == 404
    assert "nonexistent-uuid-12345" in r.json()["detail"]


@pytest.mark.asyncio
async def test_simulation_persists_analyst_summary(client: AsyncClient) -> None:
    with patch("app.api.v1.simulation.run_query", new=AsyncMock(return_value=MOCK_SIM_STATE)):
        post_r = await client.post("/api/v1/simulation", json={"n_simulations": 100})
    run_uuid = post_r.json()["run_uuid"]

    get_r = await client.get(f"/api/v1/simulation/{run_uuid}")
    assert get_r.json()["analyst_summary"] == "Brazil is the favourite to win FIFA 2026."


@pytest.mark.asyncio
async def test_simulation_persists_expected_bracket(client: AsyncClient) -> None:
    with patch("app.api.v1.simulation.run_query", new=AsyncMock(return_value=MOCK_SIM_STATE)):
        post_r = await client.post("/api/v1/simulation", json={"n_simulations": 100})
    run_uuid = post_r.json()["run_uuid"]

    get_r = await client.get(f"/api/v1/simulation/{run_uuid}")
    bracket = get_r.json()["expected_bracket"]
    assert bracket["winner"] == "BRA"

"""API tests for prediction persistence (Phase 3B)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# ── Fixtures ──────────────────────────────────────────────────────────────────

TEAM_BRA = {"name": "Brazil", "fifa_code": "BRA", "confederation": "CONMEBOL", "elo_rating": 2050.0}
TEAM_ARG = {"name": "Argentina", "fifa_code": "ARG", "confederation": "CONMEBOL", "elo_rating": 2080.0}

MOCK_PRED_STATE = {
    "prediction": {
        "home_team": "Brazil",
        "away_team": "Argentina",
        "home_code": "BRA",
        "away_code": "ARG",
        "home_win_prob": 0.40,
        "draw_prob": 0.25,
        "away_win_prob": 0.35,
        "expected_home_goals": 1.3,
        "expected_away_goals": 1.1,
        "confidence": 0.72,
        "model_version": "elo-poisson-v1",
        "explainability": "Brazil has higher ELO rating.",
    },
    "response": "Brazil vs Argentina: expect a tight contest.",
    "trace": [],
}


async def _ensure_pred_teams(client: AsyncClient) -> None:
    for team in [TEAM_BRA, TEAM_ARG]:
        r = await client.post("/api/v1/teams", json=team)
        assert r.status_code in (201, 409), r.text


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predict_saves_and_returns_id(client: AsyncClient) -> None:
    await _ensure_pred_teams(client)
    with patch("app.api.v1.predictions.run_query", new=AsyncMock(return_value=MOCK_PRED_STATE)):
        r = await client.post(
            "/api/v1/predictions",
            json={"home_team": "BRA", "away_team": "ARG", "stage": "group"},
        )
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert isinstance(body["id"], int)
    assert body["id"] > 0
    assert body["home_code"] == "BRA"
    assert body["away_code"] == "ARG"
    assert abs(body["home_win_prob"] + body["draw_prob"] + body["away_win_prob"] - 1.0) < 0.01


@pytest.mark.asyncio
async def test_get_prediction_by_id(client: AsyncClient) -> None:
    await _ensure_pred_teams(client)
    with patch("app.api.v1.predictions.run_query", new=AsyncMock(return_value=MOCK_PRED_STATE)):
        post_r = await client.post(
            "/api/v1/predictions",
            json={"home_team": "BRA", "away_team": "ARG", "stage": "sf"},
        )
    assert post_r.status_code == 200
    pred_id = post_r.json()["id"]

    get_r = await client.get(f"/api/v1/predictions/{pred_id}")
    assert get_r.status_code == 200
    body = get_r.json()
    assert body["id"] == pred_id
    assert body["home_team_code"] == "BRA"
    assert body["away_team_code"] == "ARG"
    assert body["stage"] == "sf"
    assert body["home_win_prob"] == pytest.approx(0.40)
    assert body["model_version"] == "elo-poisson-v1"


@pytest.mark.asyncio
async def test_get_prediction_not_found(client: AsyncClient) -> None:
    r = await client.get("/api/v1/predictions/999999")
    assert r.status_code == 404
    assert "999999" in r.json()["detail"]


@pytest.mark.asyncio
async def test_predict_team_not_found_returns_404(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/predictions",
        json={"home_team": "XYZ", "away_team": "ARG", "stage": "group"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_predict_persists_analyst_summary(client: AsyncClient) -> None:
    await _ensure_pred_teams(client)
    with patch("app.api.v1.predictions.run_query", new=AsyncMock(return_value=MOCK_PRED_STATE)):
        post_r = await client.post(
            "/api/v1/predictions",
            json={"home_team": "BRA", "away_team": "ARG", "stage": "qf"},
        )
    pred_id = post_r.json()["id"]

    get_r = await client.get(f"/api/v1/predictions/{pred_id}")
    assert get_r.json()["analyst_summary"] == "Brazil vs Argentina: expect a tight contest."

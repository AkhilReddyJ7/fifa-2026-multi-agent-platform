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
    assert body["home_team_code"] == "BRA"
    assert body["away_team_code"] == "ARG"
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


@pytest.mark.asyncio
async def test_predict_post_and_get_field_parity(client: AsyncClient) -> None:
    """POST response and GET response for the same record must agree on all shared fields."""
    await _ensure_pred_teams(client)
    with patch("app.api.v1.predictions.run_query", new=AsyncMock(return_value=MOCK_PRED_STATE)):
        post_r = await client.post(
            "/api/v1/predictions",
            json={"home_team": "BRA", "away_team": "ARG", "stage": "final"},
        )
    assert post_r.status_code == 200
    post_body = post_r.json()
    pred_id = post_body["id"]

    get_r = await client.get(f"/api/v1/predictions/{pred_id}")
    assert get_r.status_code == 200
    get_body = get_r.json()

    shared_fields = [
        "id",
        "home_team_code",
        "away_team_code",
        "home_win_prob",
        "draw_prob",
        "away_win_prob",
        "predicted_home_goals",
        "predicted_away_goals",
        "confidence",
        "model_version",
        "explainability",
        "analyst_summary",
    ]
    for field in shared_fields:
        assert post_body[field] == get_body[field], f"POST/GET mismatch on '{field}'"


@pytest.mark.asyncio
async def test_multiple_predictions_without_match_id(client: AsyncClient) -> None:
    """Nullable match_id allows multiple standalone predictions for the same teams."""
    await _ensure_pred_teams(client)
    with patch("app.api.v1.predictions.run_query", new=AsyncMock(return_value=MOCK_PRED_STATE)):
        r1 = await client.post(
            "/api/v1/predictions",
            json={"home_team": "BRA", "away_team": "ARG", "stage": "group"},
        )
        r2 = await client.post(
            "/api/v1/predictions",
            json={"home_team": "BRA", "away_team": "ARG", "stage": "r16"},
        )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] != r2.json()["id"]


@pytest.mark.asyncio
async def test_predict_integrity_error_returns_409(client: AsyncClient) -> None:
    """DB constraint violations must surface as 409, not 500."""
    await _ensure_pred_teams(client)
    from sqlalchemy.exc import IntegrityError as SAIntegrityError
    from sqlalchemy.ext.asyncio import AsyncSession

    async def _raise(*args, **kwargs):
        raise SAIntegrityError("stmt", {}, Exception("UNIQUE constraint failed"))

    with patch("app.api.v1.predictions.run_query", new=AsyncMock(return_value=MOCK_PRED_STATE)):
        with patch.object(AsyncSession, "flush", _raise):
            r = await client.post(
                "/api/v1/predictions",
                json={"home_team": "BRA", "away_team": "ARG", "stage": "group"},
            )
    assert r.status_code == 409

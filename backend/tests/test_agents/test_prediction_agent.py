"""Tests for prediction_agent."""

from __future__ import annotations

import pytest

from app.agents.prediction_agent import prediction_node
from app.agents.state import initial_state


@pytest.fixture
def state_with_two_teams():
    s = initial_state("Predict BRA vs ARG")
    s["intent"] = "predict"
    s["team_codes"] = ["BRA", "ARG"]
    s["team_data"] = {
        "BRA": {"id": 1, "name": "Brazil", "fifa_code": "BRA", "elo_rating": 2050, "form_index": 0.8},
        "ARG": {"id": 2, "name": "Argentina", "fifa_code": "ARG", "elo_rating": 2080, "form_index": 0.9},
        "_all_teams": [],
    }
    return s


@pytest.fixture
def state_single_team():
    s = initial_state("Analyze BRA")
    s["intent"] = "analyze"
    s["team_codes"] = ["BRA"]
    s["team_data"] = {
        "BRA": {"id": 1, "name": "Brazil", "fifa_code": "BRA", "elo_rating": 2050},
        "_all_teams": [],
    }
    return s


@pytest.mark.asyncio
async def test_prediction_node_two_teams(state_with_two_teams):
    result = await prediction_node(state_with_two_teams)

    assert "prediction" in result
    pred = result["prediction"]
    assert "home_win_prob" in pred
    assert "draw_prob" in pred
    assert "away_win_prob" in pred
    assert abs(pred["home_win_prob"] + pred["draw_prob"] + pred["away_win_prob"] - 1.0) < 0.01
    assert pred["home_code"] == "BRA"
    assert pred["away_code"] == "ARG"

    assert "trace" in result
    assert result["trace"][0]["agent"] == "prediction"


@pytest.mark.asyncio
async def test_prediction_node_single_team_skips(state_single_team):
    result = await prediction_node(state_single_team)
    pred = result.get("prediction", {})
    # With only one team, prediction should gracefully skip or error
    assert isinstance(pred, dict)


@pytest.mark.asyncio
async def test_prediction_probabilities_sum_to_one(state_with_two_teams):
    result = await prediction_node(state_with_two_teams)
    pred = result["prediction"]
    total = pred["home_win_prob"] + pred["draw_prob"] + pred["away_win_prob"]
    assert abs(total - 1.0) < 0.001

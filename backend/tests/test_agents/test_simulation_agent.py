"""Tests for simulation_agent."""

from __future__ import annotations

import pytest

from app.agents.simulation_agent import simulation_node
from app.agents.state import initial_state


def _make_teams(n: int = 16):
    teams = []
    codes = ["BRA", "ARG", "FRA", "ENG", "ESP", "GER", "POR", "NED",
             "BEL", "URU", "COL", "MEX", "USA", "SEN", "MAR", "JPN"][:n]
    groups = "ABCDEFGH"
    for i, code in enumerate(codes):
        teams.append({
            "id": i + 1,
            "name": f"Team {code}",
            "fifa_code": code,
            "elo_rating": 1800 + i * 10,
            "confederation": "UEFA",
            "group_label": groups[i % 8],
        })
    return teams


@pytest.fixture
def state_with_all_teams():
    s = initial_state("Simulate the FIFA 2026 World Cup")
    s["intent"] = "simulate"
    s["team_data"] = {"_all_teams": _make_teams(16)}
    return s


@pytest.mark.asyncio
async def test_simulation_node_returns_results(state_with_all_teams):
    result = await simulation_node(state_with_all_teams)

    assert "sim_results" in result
    sim = result["sim_results"]
    assert "win_probabilities" in sim
    assert "n_simulations" in sim
    assert sim["n_simulations"] >= 100

    assert "trace" in result
    assert result["trace"][0]["agent"] == "simulation"


@pytest.mark.asyncio
async def test_simulation_win_probs_sum_to_one(state_with_all_teams):
    result = await simulation_node(state_with_all_teams)
    win_probs = result["sim_results"]["win_probabilities"]
    assert win_probs, "Win probabilities should not be empty"
    total = sum(win_probs.values())
    assert abs(total - 1.0) < 0.02


@pytest.mark.asyncio
async def test_simulation_top5_favorites(state_with_all_teams):
    result = await simulation_node(state_with_all_teams)
    top5 = result["sim_results"].get("top_5_favorites", [])
    assert isinstance(top5, list)
    assert len(top5) <= 5

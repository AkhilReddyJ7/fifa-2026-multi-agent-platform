"""Tests for stats_agent — mocks DB session to avoid real Postgres."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.state import initial_state
from app.agents.stats_agent import stats_node


def _make_mock_session_ctx(team=None, players=None, h2h=None, stats=None, all_teams=None):
    """Create a mock async context manager that returns a fake DB session."""
    fake_db = MagicMock()
    # Mock the individual tool functions, not the session itself
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=fake_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    session_factory = MagicMock(return_value=mock_ctx)
    return session_factory, fake_db


@pytest.mark.asyncio
async def test_stats_node_with_no_team_codes():
    """State with no team_codes and chat intent skips all DB lookups."""
    state = initial_state("Tell me about the World Cup")
    state["team_codes"] = []
    state["intent"] = "chat"

    fake_db = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=fake_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    # chat intent: no team_codes AND intent not in (simulate, analyze) — _all_teams skipped
    with (
        patch("app.agents.stats_agent.AsyncSessionLocal", return_value=mock_ctx),
        patch("app.agents.stats_agent.get_all_teams", new_callable=AsyncMock, return_value=[]),
    ):
        result = await stats_node(state)

    assert "team_data" in result
    assert "trace" in result
    assert result["trace"][0]["agent"] == "stats"
    assert "head_to_head" in result["team_data"]


@pytest.mark.asyncio
async def test_stats_node_simulate_intent_fetches_all_teams():
    """Simulate intent triggers get_all_teams call."""
    state = initial_state("Simulate the tournament")
    state["team_codes"] = []
    state["intent"] = "simulate"

    fake_db = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=fake_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    fake_all = [{"id": 1, "name": "Brazil", "fifa_code": "BRA", "elo_rating": 2050}]

    with (
        patch("app.agents.stats_agent.AsyncSessionLocal", return_value=mock_ctx),
        patch("app.agents.stats_agent.get_all_teams", new_callable=AsyncMock, return_value=fake_all),
    ):
        result = await stats_node(state)

    assert result["team_data"].get("_all_teams") == fake_all
    assert result["trace"][0]["agent"] == "stats"


@pytest.mark.asyncio
async def test_stats_node_two_teams():
    """With two team codes, fetches both teams, players, stats, and H2H."""
    state = initial_state("BRA vs ARG")
    state["team_codes"] = ["BRA", "ARG"]
    state["intent"] = "predict"

    fake_bra = {"id": 1, "name": "Brazil", "fifa_code": "BRA", "elo_rating": 2050}
    fake_arg = {"id": 2, "name": "Argentina", "fifa_code": "ARG", "elo_rating": 2080}
    fake_players = [{"id": 1, "name": "Neymar", "position": "FWD"}]
    fake_h2h = [{"id": 10, "home_team_id": 1, "away_team_id": 2}]

    fake_db = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=fake_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    def _team_by_code_side(db, code):
        return fake_bra if code == "BRA" else fake_arg

    with (
        patch("app.agents.stats_agent.AsyncSessionLocal", return_value=mock_ctx),
        patch("app.agents.stats_agent.get_team_by_code", new_callable=AsyncMock, side_effect=_team_by_code_side),
        patch("app.agents.stats_agent.get_team_players", new_callable=AsyncMock, return_value=fake_players),
        patch("app.agents.stats_agent.get_team_match_stats", new_callable=AsyncMock, return_value=[]),
        patch("app.agents.stats_agent.get_head_to_head", new_callable=AsyncMock, return_value=fake_h2h),
    ):
        result = await stats_node(state)

    td = result["team_data"]
    assert "BRA" in td
    assert "ARG" in td
    assert td["BRA"]["elo_rating"] == 2050
    assert td["head_to_head"] == fake_h2h

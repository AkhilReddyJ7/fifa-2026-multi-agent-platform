"""Tests for orchestrator — intent classification, team extraction, graph routing."""

from __future__ import annotations


import pytest

from app.agents.orchestrator import _classify_intent, _extract_teams, orchestrator_node
from app.agents.state import initial_state


# ── Unit: intent classifier ───────────────────────────────────────────────────

@pytest.mark.parametrize("query,expected", [
    ("Predict BRA vs ARG", "predict"),
    ("Who wins between FRA and GER?", "predict"),
    ("Simulate the FIFA 2026 World Cup tournament", "simulate"),
    ("Show champion probabilities for the bracket", "simulate"),
    # Explicit "simulate" must win over predict phrases like "who wins"
    ("Simulate the tournament, who wins the World Cup?", "simulate"),
    ("Simulate BRA vs ARG in the group stage", "simulate"),
    # Stem matching: bare stems used to fail on their own full words
    ("Simulate the group stage", "simulate"),
    ("Who will be champions in 2026?", "simulate"),
    ("Analyze GER", "analyze"),
    ("Analyze Brazil's squad and tactics", "analyze"),
    ("Show me Brazil's match statistics", "lookup"),
    ("Tell me about the World Cup", "chat"),
])
def test_classify_intent(query, expected):
    assert _classify_intent(query) == expected


@pytest.mark.parametrize("query,expected", [
    ("Predict BRA vs ARG", ["BRA", "ARG"]),
    ("How will FRA perform in the tournament?", ["FRA"]),
    ("World Cup analysis", []),
    ("BRA vs ENG in the final", ["BRA", "ENG"]),
])
def test_extract_teams(query, expected):
    result = _extract_teams(query)
    assert result == expected


# ── Integration: orchestrator_node ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_orchestrator_node_sets_intent_and_teams():
    state = initial_state("Predict BRA vs ARG in the final")
    result = await orchestrator_node(state)

    assert result["intent"] == "predict"
    assert "BRA" in result["team_codes"]
    assert "ARG" in result["team_codes"]
    assert len(result["trace"]) == 1
    assert result["trace"][0]["agent"] == "orchestrator"


@pytest.mark.asyncio
async def test_orchestrator_node_simulate_intent():
    state = initial_state("Simulate the entire World Cup tournament")
    result = await orchestrator_node(state)
    assert result["intent"] == "simulate"


@pytest.mark.asyncio
async def test_routing_predict_goes_to_prediction_then_research():
    """Verify _route_after_stats returns 'prediction' for predict intent with 2 teams."""
    from app.agents.orchestrator import _route_after_stats
    from app.agents.state import initial_state

    state = initial_state("Predict BRA vs ARG")
    state["intent"] = "predict"
    state["team_codes"] = ["BRA", "ARG"]
    assert _route_after_stats(state) == "prediction"


@pytest.mark.asyncio
async def test_routing_simulate_goes_to_simulation():
    from app.agents.orchestrator import _route_after_stats
    from app.agents.state import initial_state

    state = initial_state("Simulate the tournament")
    state["intent"] = "simulate"
    state["team_codes"] = []
    assert _route_after_stats(state) == "simulation"


@pytest.mark.asyncio
async def test_routing_chat_goes_to_research():
    from app.agents.orchestrator import _route_after_stats
    from app.agents.state import initial_state

    state = initial_state("Tell me about Brazil")
    state["intent"] = "chat"
    state["team_codes"] = ["BRA"]
    assert _route_after_stats(state) == "research"


def test_build_graph_compiles_with_and_without_analyst():
    from app.agents.orchestrator import build_graph

    full = build_graph(include_analyst=True)
    partial = build_graph(include_analyst=False)
    assert "analyst" in full.get_graph().nodes
    assert "analyst" not in partial.get_graph().nodes
    # Both variants must route through the specialist agents
    for g in (full, partial):
        nodes = g.get_graph().nodes
        assert {"orchestrator", "stats", "prediction_agent", "simulation", "research"} <= set(nodes)

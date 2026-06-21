"""Tests for orchestrator — intent classification, team extraction, graph routing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.orchestrator import _classify_intent, _extract_teams, orchestrator_node
from app.agents.state import initial_state


# ── Unit: intent classifier ───────────────────────────────────────────────────

@pytest.mark.parametrize("query,expected", [
    ("Predict BRA vs ARG", "predict"),
    ("Who wins between FRA and GER?", "predict"),
    ("Simulate the FIFA 2026 World Cup tournament", "simulate"),
    ("Show champion probabilities for the bracket", "simulate"),
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


# ── Phase 4B: checkpointing tests ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_query_with_thread_id_passes_config_to_ainvoke(monkeypatch):
    """run_query with thread_id calls checkpointed graph with the correct config."""
    import app.agents.orchestrator as orch_module

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"response": "ok", "trace": []})
    monkeypatch.setattr(orch_module, "_graph_checkpointed", mock_graph)

    await orch_module.run_query("test query", thread_id="test-uuid-123")

    mock_graph.ainvoke.assert_awaited_once()
    call_kwargs = mock_graph.ainvoke.call_args.kwargs
    assert call_kwargs.get("config") == {"configurable": {"thread_id": "test-uuid-123"}}


@pytest.mark.asyncio
async def test_run_query_without_thread_id_is_stateless(monkeypatch):
    """run_query without thread_id calls the fallback graph with no config."""
    import app.agents.orchestrator as orch_module

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"response": "stateless", "trace": []})
    monkeypatch.setattr(orch_module, "_graph_fallback", mock_graph)
    monkeypatch.setattr(orch_module, "_graph_checkpointed", None)

    await orch_module.run_query("test query")

    mock_graph.ainvoke.assert_awaited_once()
    assert "config" not in mock_graph.ainvoke.call_args.kwargs


def test_build_graph_with_memory_saver_compiles():
    """build_graph(checkpointer=MemorySaver()) compiles without error."""
    from langgraph.checkpoint.memory import MemorySaver
    from app.agents.orchestrator import build_graph

    graph = build_graph(checkpointer=MemorySaver())
    assert graph is not None


@pytest.mark.asyncio
async def test_run_query_falls_back_on_redis_error(monkeypatch):
    """When checkpointed graph raises RedisError, run_query falls back to stateless."""
    import redis.exceptions
    import app.agents.orchestrator as orch_module

    mock_checkpointed = MagicMock()
    mock_checkpointed.ainvoke = AsyncMock(
        side_effect=redis.exceptions.ConnectionError("Redis unavailable")
    )
    mock_fallback = MagicMock()
    mock_fallback.ainvoke = AsyncMock(return_value={"response": "fallback ok", "trace": []})

    monkeypatch.setattr(orch_module, "_graph_checkpointed", mock_checkpointed)
    monkeypatch.setattr(orch_module, "_graph_fallback", mock_fallback)

    result = await orch_module.run_query("query", thread_id="test-uuid-123")

    mock_checkpointed.ainvoke.assert_awaited_once()
    mock_fallback.ainvoke.assert_awaited_once()
    assert result["response"] == "fallback ok"


# ── Phase 6A: LangSmith tracing tests ────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_query_completes_without_langsmith_env_vars(monkeypatch):
    """run_query completes without error when LangSmith env vars are absent."""
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)

    import app.agents.orchestrator as orch_module

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={"response": "ok", "trace": []})
    monkeypatch.setattr(orch_module, "_graph_fallback", mock_graph)
    monkeypatch.setattr(orch_module, "_graph_checkpointed", None)

    result = await orch_module.run_query("who wins Brazil vs Argentina")
    assert isinstance(result, dict)
    assert "response" in result


def test_run_query_is_decorated_with_traceable():
    """run_query carries the @traceable wrapper from langsmith."""
    from app.agents.orchestrator import run_query
    assert hasattr(run_query, "__wrapped__")


def test_llm_function_is_decorated_with_traceable():
    """chat_complete in llm.py carries the @traceable wrapper from langsmith."""
    from app.core.llm import chat_complete
    assert hasattr(chat_complete, "__wrapped__")


def test_settings_langsmith_tracing_disabled_by_default(monkeypatch):
    """Settings() disables LangSmith tracing when env vars are absent."""
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGCHAIN_ENDPOINT", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING_ENABLED", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)

    from app.core.config import Settings
    s = Settings()
    assert s.langsmith_tracing_enabled is False
    assert not s.langsmith_api_key


def test_settings_langsmith_tracing_enabled_when_env_vars_set(monkeypatch):
    """Settings() enables tracing when LANGCHAIN_TRACING_V2=true is set."""
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "test-project")

    from app.core.config import Settings
    s = Settings()
    assert s.langsmith_tracing_enabled is True
    assert s.langsmith_project == "test-project"

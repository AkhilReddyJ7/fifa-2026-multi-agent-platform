"""API tests for Phase 3C: chat session persistence."""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# ── Fixtures ──────────────────────────────────────────────────────────────────

MOCK_CHAT_STATE = {
    "response": "Brazil is the strongest team in CONMEBOL.",
    "trace": [
        {
            "agent": "analyst",
            "input_keys": ["query"],
            "output_keys": ["response"],
            "duration_ms": 42.0,
            "notes": "ok",
        }
    ],
}

_PATCH = "app.api.v1.chat.run_query"


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_no_session_id_creates_session(authenticated_client: AsyncClient) -> None:
    """POST without session_id → new UUID session returned."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r = await authenticated_client.post("/api/v1/chat", json={"message": "Tell me about Brazil."})
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert len(body["session_id"]) == 36  # UUID length
    assert body["response"] == MOCK_CHAT_STATE["response"]


@pytest.mark.asyncio
async def test_chat_resumes_existing_session(authenticated_client: AsyncClient) -> None:
    """POST with a known session_uuid adds to that session (same UUID returned)."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r1 = await authenticated_client.post("/api/v1/chat", json={"message": "First message."})
    session_id = r1.json()["session_id"]

    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r2 = await authenticated_client.post("/api/v1/chat", json={"message": "Follow-up.", "session_id": session_id})
    assert r2.status_code == 200
    assert r2.json()["session_id"] == session_id


@pytest.mark.asyncio
async def test_chat_unknown_session_id_creates_new(authenticated_client: AsyncClient) -> None:
    """POST with an unrecognised session_uuid silently creates a new session."""
    unknown = "00000000-0000-0000-0000-000000000000"
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r = await authenticated_client.post("/api/v1/chat", json={"message": "Hello.", "session_id": unknown})
    assert r.status_code == 200
    assert r.json()["session_id"] != unknown


@pytest.mark.asyncio
async def test_messages_persisted_with_correct_roles(authenticated_client: AsyncClient) -> None:
    """After a chat POST, GET session shows user and assistant messages in order."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r = await authenticated_client.post("/api/v1/chat", json={"message": "Who will win the World Cup?"})
    session_id = r.json()["session_id"]

    get_r = await authenticated_client.get(f"/api/v1/chat/{session_id}")
    assert get_r.status_code == 200
    messages = get_r.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Who will win the World Cup?"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == MOCK_CHAT_STATE["response"]


@pytest.mark.asyncio
async def test_agent_trace_persisted_on_assistant_message(authenticated_client: AsyncClient) -> None:
    """agent_trace JSON is stored on the assistant ChatMessage row."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r = await authenticated_client.post("/api/v1/chat", json={"message": "Predict ARG vs BRA."})
    session_id = r.json()["session_id"]

    get_r = await authenticated_client.get(f"/api/v1/chat/{session_id}")
    messages = get_r.json()["messages"]
    assistant = next(m for m in messages if m["role"] == "assistant")
    assert isinstance(assistant["agent_trace"], list)
    assert len(assistant["agent_trace"]) == 1
    assert assistant["agent_trace"][0]["agent"] == "analyst"


@pytest.mark.asyncio
async def test_get_session_returns_ordered_history(authenticated_client: AsyncClient) -> None:
    """Two chat turns produce 4 messages (user+assistant×2) in chronological order."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r1 = await authenticated_client.post("/api/v1/chat", json={"message": "First."})
    session_id = r1.json()["session_id"]

    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        await authenticated_client.post("/api/v1/chat", json={"message": "Second.", "session_id": session_id})

    get_r = await authenticated_client.get(f"/api/v1/chat/{session_id}")
    assert get_r.status_code == 200
    messages = get_r.json()["messages"]
    assert len(messages) == 4
    assert messages[0]["content"] == "First."
    assert messages[0]["role"] == "user"
    assert messages[2]["content"] == "Second."
    assert messages[2]["role"] == "user"


@pytest.mark.asyncio
async def test_get_session_not_found(authenticated_client: AsyncClient) -> None:
    """GET unknown session_uuid → 404."""
    r = await authenticated_client.get("/api/v1/chat/00000000-0000-0000-0000-999999999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_removes_it(authenticated_client: AsyncClient) -> None:
    """DELETE session → 204; subsequent GET → 404."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r = await authenticated_client.post("/api/v1/chat", json={"message": "Delete me."})
    session_id = r.json()["session_id"]

    del_r = await authenticated_client.delete(f"/api/v1/chat/{session_id}")
    assert del_r.status_code == 204

    get_r = await authenticated_client.get(f"/api/v1/chat/{session_id}")
    assert get_r.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_not_found(authenticated_client: AsyncClient) -> None:
    """DELETE unknown session_uuid → 404."""
    r = await authenticated_client.delete("/api/v1/chat/00000000-0000-0000-0000-888888888888")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_history_passed_to_orchestrator_on_second_turn(authenticated_client: AsyncClient) -> None:
    """On a second turn, run_query receives prior messages in extra_state['history']."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r1 = await authenticated_client.post("/api/v1/chat", json={"message": "First turn."})
    session_id = r1.json()["session_id"]

    second_mock = AsyncMock(return_value=MOCK_CHAT_STATE)
    with patch(_PATCH, new=second_mock):
        await authenticated_client.post("/api/v1/chat", json={"message": "Second turn.", "session_id": session_id})

    second_mock.assert_awaited_once()
    _, kwargs = second_mock.call_args
    extra = kwargs.get("extra_state", {})
    assert "history" in extra
    assert len(extra["history"]) >= 2  # at least user + assistant from turn 1
    assert extra["history"][0]["role"] == "user"
    assert extra["history"][0]["content"] == "First turn."


@pytest.mark.asyncio
async def test_session_id_from_other_user_creates_new_session(authenticated_client: AsyncClient) -> None:
    """Using another user's session_uuid must create a new session, not hijack it."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r1 = await authenticated_client.post("/api/v1/chat", json={"message": "User A's message."})
    user_a_session_id = r1.json()["session_id"]

    # Register and log in as User B using the same test client
    await authenticated_client.post(
        "/api/v1/auth/register",
        json={"email": "userb@example.com", "password": "testpass123"},
    )
    login_r = await authenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "userb@example.com", "password": "testpass123"},
    )
    user_b_token = login_r.json()["access_token"]

    # User B sends a message using User A's session_id — should get a new session
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r2 = await authenticated_client.post(
            "/api/v1/chat",
            json={"message": "User B's message.", "session_id": user_a_session_id},
            headers={"Authorization": f"Bearer {user_b_token}"},
        )
    assert r2.status_code == 200
    assert r2.json()["session_id"] != user_a_session_id


# ── Streaming patch targets ───────────────────────────────────────────────────

_ORCH = "app.agents.orchestrator.orchestrator_node"
_STATS = "app.agents.stats_agent.stats_node"
_PRED = "app.agents.prediction_agent.prediction_node"
_SIM = "app.agents.simulation_agent.simulation_node"
_RESEARCH = "app.agents.research_agent.research_node"
_ANALYST_STREAM = "app.api.v1.chat.analyst_stream"


async def _fake_stream(state):  # noqa: ANN001
    yield "simulated response"


# ── Streaming tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_simulate_invokes_simulation_node(authenticated_client: AsyncClient) -> None:
    """Streaming with simulate intent must invoke simulation_node (Phase 4A-Lite fix)."""
    sim_mock = AsyncMock(return_value={"sim_results": {"win_probabilities": {"BRA": 0.2}}, "trace": []})
    with (
        patch(_ORCH, new=AsyncMock(return_value={"intent": "simulate", "team_codes": [], "trace": []})),
        patch(_STATS, new=AsyncMock(return_value={"team_data": {}, "trace": []})),
        patch(_SIM, new=sim_mock),
        patch(_RESEARCH, new=AsyncMock(return_value={"rag_docs": [], "trace": []})),
        patch(_ANALYST_STREAM, new=_fake_stream),
    ):
        r = await authenticated_client.post("/api/v1/chat/stream", json={"message": "Simulate the 2026 World Cup."})

    assert r.status_code == 200
    sim_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_stream_predict_does_not_invoke_simulation_node(authenticated_client: AsyncClient) -> None:
    """Streaming with predict intent must NOT invoke simulation_node (elif correctness)."""
    sim_mock = AsyncMock(return_value={"sim_results": {}, "trace": []})
    pred_mock = AsyncMock(return_value={"prediction": {"home_win_prob": 0.5}, "trace": []})
    with (
        patch(_ORCH, new=AsyncMock(return_value={"intent": "predict", "team_codes": ["BRA", "ARG"], "trace": []})),
        patch(_STATS, new=AsyncMock(return_value={"team_data": {}, "trace": []})),
        patch(_PRED, new=pred_mock),
        patch(_SIM, new=sim_mock),
        patch(_RESEARCH, new=AsyncMock(return_value={"rag_docs": [], "trace": []})),
        patch(_ANALYST_STREAM, new=_fake_stream),
    ):
        r = await authenticated_client.post("/api/v1/chat/stream", json={"message": "Predict BRA vs ARG."})

    assert r.status_code == 200
    pred_mock.assert_awaited_once()
    sim_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_stream_returns_sse_and_persists_assistant_message(authenticated_client: AsyncClient) -> None:
    """Streaming response emits SSE events and persists the assistant message to the DB."""
    with (
        patch(_ORCH, new=AsyncMock(return_value={"intent": "chat", "team_codes": [], "trace": []})),
        patch(_STATS, new=AsyncMock(return_value={"team_data": {}, "trace": []})),
        patch(_RESEARCH, new=AsyncMock(return_value={"rag_docs": [], "trace": []})),
        patch(_ANALYST_STREAM, new=_fake_stream),
    ):
        r = await authenticated_client.post("/api/v1/chat/stream", json={"message": "Hello World Cup!"})

    assert r.status_code == 200
    text = r.text
    assert "data: [START]" in text
    assert "data: [DONE]" in text
    assert "simulated response" in text

    m = re.search(r'"session_uuid":"([^"]+)"', text)
    assert m is not None
    session_uuid = m.group(1)

    get_r = await authenticated_client.get(f"/api/v1/chat/{session_uuid}")
    assert get_r.status_code == 200
    messages = get_r.json()["messages"]
    assert any(msg["role"] == "assistant" and msg["content"] == "simulated response" for msg in messages)


# ── Phase 4B: checkpointing tests ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_endpoint_passes_session_uuid_as_thread_id(authenticated_client: AsyncClient) -> None:
    """POST /api/v1/chat passes the session UUID as thread_id to run_query."""
    mock = AsyncMock(return_value=MOCK_CHAT_STATE)
    with patch(_PATCH, new=mock):
        r = await authenticated_client.post("/api/v1/chat", json={"message": "Hello."})
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    mock.assert_awaited_once()
    call_kwargs = mock.call_args.kwargs
    assert call_kwargs.get("thread_id") == session_id


@pytest.mark.asyncio
async def test_chat_stream_endpoint_does_not_pass_thread_id(authenticated_client: AsyncClient) -> None:
    """POST /api/v1/chat/stream does not call run_query (streaming uses manual node chain)."""
    mock = AsyncMock(return_value=MOCK_CHAT_STATE)
    with (
        patch(_PATCH, new=mock),
        patch(_ORCH, new=AsyncMock(return_value={"intent": "chat", "team_codes": [], "trace": []})),
        patch(_STATS, new=AsyncMock(return_value={"team_data": {}, "trace": []})),
        patch(_RESEARCH, new=AsyncMock(return_value={"rag_docs": [], "trace": []})),
        patch(_ANALYST_STREAM, new=_fake_stream),
    ):
        r = await authenticated_client.post("/api/v1/chat/stream", json={"message": "Stream me."})

    assert r.status_code == 200
    mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_multiturn_memory_with_memory_saver(memory_saver, monkeypatch) -> None:
    """Using MemorySaver, run_query called twice with same thread_id preserves history."""
    import app.agents.orchestrator as orch_module
    from app.agents.state import AgentTrace

    thread_id = "multi-turn-memory-456"

    async def _mock_orch(state):
        return {
            "intent": "chat",
            "team_codes": [],
            "trace": [AgentTrace(agent="orchestrator", input_keys=[], output_keys=[], duration_ms=0.0, notes="")],
        }

    async def _mock_stats(state):
        return {
            "team_data": {},
            "trace": [AgentTrace(agent="stats", input_keys=[], output_keys=[], duration_ms=0.0, notes="")],
        }

    async def _mock_research(state):
        return {
            "rag_docs": [],
            "trace": [AgentTrace(agent="research", input_keys=[], output_keys=[], duration_ms=0.0, notes="")],
        }

    async def _mock_analyst(state):
        return {
            "response": f"Answer: {state.get('query', '')}",
            "trace": [AgentTrace(agent="analyst", input_keys=[], output_keys=[], duration_ms=0.0, notes="")],
        }

    monkeypatch.setattr(orch_module, "orchestrator_node", _mock_orch)
    monkeypatch.setattr(orch_module, "stats_node", _mock_stats)
    monkeypatch.setattr(orch_module, "research_node", _mock_research)
    monkeypatch.setattr(orch_module, "analyst_node", _mock_analyst)

    checkpointed = orch_module.build_graph(checkpointer=memory_saver)
    monkeypatch.setattr(orch_module, "_graph_checkpointed", checkpointed)

    result1 = await orch_module.run_query("question one", thread_id=thread_id)
    assert result1.get("response") == "Answer: question one"

    result2 = await orch_module.run_query(
        "question two",
        extra_state={"history": [{"role": "assistant", "content": result1.get("response", "")}]},
        thread_id=thread_id,
    )
    assert result2.get("history") is not None
    assert any(h.get("content") == result1.get("response") for h in result2.get("history", []))

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
async def test_chat_no_session_id_creates_session(client: AsyncClient) -> None:
    """POST without session_id → new UUID session returned."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r = await client.post("/api/v1/chat", json={"message": "Tell me about Brazil."})
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert len(body["session_id"]) == 36  # UUID length
    assert body["response"] == MOCK_CHAT_STATE["response"]


@pytest.mark.asyncio
async def test_chat_resumes_existing_session(client: AsyncClient) -> None:
    """POST with a known session_uuid adds to that session (same UUID returned)."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r1 = await client.post("/api/v1/chat", json={"message": "First message."})
    session_id = r1.json()["session_id"]

    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r2 = await client.post("/api/v1/chat", json={"message": "Follow-up.", "session_id": session_id})
    assert r2.status_code == 200
    assert r2.json()["session_id"] == session_id


@pytest.mark.asyncio
async def test_chat_unknown_session_id_creates_new(client: AsyncClient) -> None:
    """POST with an unrecognised session_uuid silently creates a new session."""
    unknown = "00000000-0000-0000-0000-000000000000"
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r = await client.post("/api/v1/chat", json={"message": "Hello.", "session_id": unknown})
    assert r.status_code == 200
    assert r.json()["session_id"] != unknown


@pytest.mark.asyncio
async def test_messages_persisted_with_correct_roles(client: AsyncClient) -> None:
    """After a chat POST, GET session shows user and assistant messages in order."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r = await client.post("/api/v1/chat", json={"message": "Who will win the World Cup?"})
    session_id = r.json()["session_id"]

    get_r = await client.get(f"/api/v1/chat/{session_id}")
    assert get_r.status_code == 200
    messages = get_r.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Who will win the World Cup?"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == MOCK_CHAT_STATE["response"]


@pytest.mark.asyncio
async def test_agent_trace_persisted_on_assistant_message(client: AsyncClient) -> None:
    """agent_trace JSON is stored on the assistant ChatMessage row."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r = await client.post("/api/v1/chat", json={"message": "Predict ARG vs BRA."})
    session_id = r.json()["session_id"]

    get_r = await client.get(f"/api/v1/chat/{session_id}")
    messages = get_r.json()["messages"]
    assistant = next(m for m in messages if m["role"] == "assistant")
    assert isinstance(assistant["agent_trace"], list)
    assert len(assistant["agent_trace"]) == 1
    assert assistant["agent_trace"][0]["agent"] == "analyst"


@pytest.mark.asyncio
async def test_get_session_returns_ordered_history(client: AsyncClient) -> None:
    """Two chat turns produce 4 messages (user+assistant×2) in chronological order."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r1 = await client.post("/api/v1/chat", json={"message": "First."})
    session_id = r1.json()["session_id"]

    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        await client.post("/api/v1/chat", json={"message": "Second.", "session_id": session_id})

    get_r = await client.get(f"/api/v1/chat/{session_id}")
    assert get_r.status_code == 200
    messages = get_r.json()["messages"]
    assert len(messages) == 4
    assert messages[0]["content"] == "First."
    assert messages[0]["role"] == "user"
    assert messages[2]["content"] == "Second."
    assert messages[2]["role"] == "user"


@pytest.mark.asyncio
async def test_get_session_not_found(client: AsyncClient) -> None:
    """GET unknown session_uuid → 404."""
    r = await client.get("/api/v1/chat/00000000-0000-0000-0000-999999999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_removes_it(client: AsyncClient) -> None:
    """DELETE session → 204; subsequent GET → 404."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r = await client.post("/api/v1/chat", json={"message": "Delete me."})
    session_id = r.json()["session_id"]

    del_r = await client.delete(f"/api/v1/chat/{session_id}")
    assert del_r.status_code == 204

    get_r = await client.get(f"/api/v1/chat/{session_id}")
    assert get_r.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_not_found(client: AsyncClient) -> None:
    """DELETE unknown session_uuid → 404."""
    r = await client.delete("/api/v1/chat/00000000-0000-0000-0000-888888888888")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_history_passed_to_orchestrator_on_second_turn(client: AsyncClient) -> None:
    """On a second turn, run_query receives prior messages in extra_state['history']."""
    with patch(_PATCH, new=AsyncMock(return_value=MOCK_CHAT_STATE)):
        r1 = await client.post("/api/v1/chat", json={"message": "First turn."})
    session_id = r1.json()["session_id"]

    second_mock = AsyncMock(return_value=MOCK_CHAT_STATE)
    with patch(_PATCH, new=second_mock):
        await client.post("/api/v1/chat", json={"message": "Second turn.", "session_id": session_id})

    second_mock.assert_awaited_once()
    _, kwargs = second_mock.call_args
    extra = kwargs.get("extra_state", {})
    assert "history" in extra
    assert len(extra["history"]) >= 2  # at least user + assistant from turn 1
    assert extra["history"][0]["role"] == "user"
    assert extra["history"][0]["content"] == "First turn."


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
async def test_stream_simulate_invokes_simulation_node(client: AsyncClient) -> None:
    """Streaming with simulate intent must invoke simulation_node (Phase 4A-Lite fix)."""
    sim_mock = AsyncMock(return_value={"sim_results": {"win_probabilities": {"BRA": 0.2}}, "trace": []})
    with (
        patch(_ORCH, new=AsyncMock(return_value={"intent": "simulate", "team_codes": [], "trace": []})),
        patch(_STATS, new=AsyncMock(return_value={"team_data": {}, "trace": []})),
        patch(_SIM, new=sim_mock),
        patch(_RESEARCH, new=AsyncMock(return_value={"rag_docs": [], "trace": []})),
        patch(_ANALYST_STREAM, new=_fake_stream),
    ):
        r = await client.post("/api/v1/chat/stream", json={"message": "Simulate the 2026 World Cup."})

    assert r.status_code == 200
    sim_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_stream_predict_does_not_invoke_simulation_node(client: AsyncClient) -> None:
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
        r = await client.post("/api/v1/chat/stream", json={"message": "Predict BRA vs ARG."})

    assert r.status_code == 200
    pred_mock.assert_awaited_once()
    sim_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_stream_returns_sse_and_persists_assistant_message(client: AsyncClient) -> None:
    """Streaming response emits SSE events and persists the assistant message to the DB."""
    with (
        patch(_ORCH, new=AsyncMock(return_value={"intent": "chat", "team_codes": [], "trace": []})),
        patch(_STATS, new=AsyncMock(return_value={"team_data": {}, "trace": []})),
        patch(_RESEARCH, new=AsyncMock(return_value={"rag_docs": [], "trace": []})),
        patch(_ANALYST_STREAM, new=_fake_stream),
    ):
        r = await client.post("/api/v1/chat/stream", json={"message": "Hello World Cup!"})

    assert r.status_code == 200
    text = r.text
    assert "data: [START]" in text
    assert "data: [DONE]" in text
    assert "simulated response" in text

    m = re.search(r'"session_uuid":"([^"]+)"', text)
    assert m is not None
    session_uuid = m.group(1)

    get_r = await client.get(f"/api/v1/chat/{session_uuid}")
    assert get_r.status_code == 200
    messages = get_r.json()["messages"]
    assert any(msg["role"] == "assistant" and msg["content"] == "simulated response" for msg in messages)

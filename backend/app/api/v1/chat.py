"""Chat API — session persistence and streaming analyst responses via SSE."""

from __future__ import annotations

import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.analyst_agent import analyst_stream
from app.agents.orchestrator import run_query
from app.agents.state import initial_state
from app.api.deps import get_db
from app.db.models import ChatMessage, ChatSession
from app.schemas.chat import ChatMessageRead, ChatSessionRead

router = APIRouter()

HISTORY_LIMIT = 10  # prior messages to pass as LLM context


# ── Request / response schemas ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    agent_trace: list


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_create_session(
    session_id: str | None,
    db: AsyncSession,
) -> ChatSession:
    """Return existing ChatSession by UUID or create a new one."""
    if session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.session_uuid == session_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
    new_session = ChatSession(session_uuid=str(uuid.uuid4()))
    db.add(new_session)
    await db.flush()
    return new_session


async def _load_history(session: ChatSession, db: AsyncSession) -> list[dict[str, str]]:
    """Return the last HISTORY_LIMIT messages as [{"role": …, "content": …}]."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id.desc())
        .limit(HISTORY_LIMIT)
    )
    msgs = list(reversed(result.scalars().all()))
    return [{"role": m.role, "content": m.content} for m in msgs]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse, summary="Chat with the AI analyst")
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Non-streaming chat — persists both turns and returns the complete response."""
    session = await _get_or_create_session(payload.session_id, db)
    history = await _load_history(session, db)

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message))
    await db.flush()

    final_state = await run_query(payload.message, extra_state={"history": history})

    response_text = final_state.get("response", "")
    trace = final_state.get("trace", [])

    db.add(ChatMessage(
        session_id=session.id,
        role="assistant",
        content=response_text,
        agent_trace=trace,  # type: ignore[arg-type]
    ))
    await db.flush()

    return ChatResponse(
        session_id=session.session_uuid,
        response=response_text,
        agent_trace=trace,
    )


@router.post("/stream", summary="Chat with streaming SSE response")
async def chat_stream_endpoint(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Streaming chat via SSE — persists both turns; final event carries session_uuid."""
    session = await _get_or_create_session(payload.session_id, db)
    history = await _load_history(session, db)

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message))
    await db.flush()

    session_uuid = session.session_uuid
    session_db_id = session.id

    async def event_generator() -> AsyncGenerator[str, None]:
        from app.agents.orchestrator import orchestrator_node
        from app.agents.prediction_agent import prediction_node
        from app.agents.research_agent import research_node
        from app.agents.stats_agent import stats_node

        state = initial_state(payload.message, history=history)
        state = {**state, **(await orchestrator_node(state))}  # type: ignore[typeddict-item]
        state = {**state, **(await stats_node(state))}  # type: ignore[typeddict-item]

        intent = state.get("intent", "chat")
        if intent == "predict" and len(state.get("team_codes", [])) >= 2:
            state = {**state, **(await prediction_node(state))}  # type: ignore[typeddict-item]

        state = {**state, **(await research_node(state))}  # type: ignore[typeddict-item]

        chunks: list[str] = []
        yield "data: [START]\n\n"
        async for chunk in analyst_stream(state):  # type: ignore[arg-type]
            chunks.append(chunk)
            yield f"data: {chunk.replace(chr(10), chr(92) + 'n')}\n\n"

        full_response = "".join(chunks)
        db.add(ChatMessage(
            session_id=session_db_id,
            role="assistant",
            content=full_response,
        ))
        await db.flush()

        yield f'data: {{"event":"session","session_uuid":"{session_uuid}"}}\n\n'
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{session_uuid}", response_model=ChatSessionRead, summary="Get session with message history")
async def get_session(
    session_uuid: str,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionRead:
    """Return a chat session and its full message history in chronological order."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_uuid == session_uuid)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_uuid!r} not found")

    msgs_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id)
    )
    messages = [
        ChatMessageRead.model_validate(m)
        for m in msgs_result.scalars().all()
    ]

    return ChatSessionRead(
        session_uuid=session.session_uuid,
        user_id=session.user_id,
        created_at=session.created_at,
        messages=messages,
    )


@router.delete("/{session_uuid}", status_code=204, response_class=Response, summary="Delete a chat session")
async def delete_session(
    session_uuid: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a session and all its messages (cascade)."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_uuid == session_uuid)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_uuid!r} not found")
    await db.delete(session)
    await db.flush()
    return Response(status_code=204)

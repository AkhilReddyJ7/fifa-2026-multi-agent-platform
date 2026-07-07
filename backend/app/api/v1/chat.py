"""Chat API — streaming analyst responses via Server-Sent Events."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.analyst_agent import analyst_stream
from app.agents.orchestrator import run_query

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    agent_trace: list


@router.post("", response_model=ChatResponse, summary="Chat with the AI analyst")
async def chat(payload: ChatRequest) -> ChatResponse:
    """Non-streaming chat — returns complete response."""
    final_state = await run_query(payload.message)
    return ChatResponse(
        session_id=payload.session_id or str(uuid.uuid4()),
        response=final_state.get("response", ""),
        agent_trace=final_state.get("trace", []),
    )


@router.post("/stream", summary="Chat with streaming SSE response")
async def chat_stream_endpoint(payload: ChatRequest) -> StreamingResponse:
    """Streaming chat via SSE.

    Runs the compiled agent graph (same topology as /chat, so simulate-intent
    queries get the simulation agent too), emitting an `[AGENT:<name>]` event
    as each agent finishes, then streams the analyst's tokens between
    `[START]` and `[DONE]`.
    """

    async def event_generator():
        from app.agents.orchestrator import stream_pipeline

        state = None
        async for kind, value in stream_pipeline(payload.message):
            if kind == "node":
                yield f"data: [AGENT:{value}]\n\n"
            else:
                state = value

        yield "data: [START]\n\n"
        async for chunk in analyst_stream(state):
            # SSE format; escape backslashes before newlines so the client
            # can invert the encoding without corrupting literal "\n" text
            safe = chunk.replace("\\", "\\\\").replace("\n", "\\n")
            yield f"data: {safe}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

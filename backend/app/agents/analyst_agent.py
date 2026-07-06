"""Analyst Agent — synthesises all agent outputs into a final response via LLM."""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator, Dict

import structlog

from app.agents.state import AgentTrace, PlatformState
from app.core.llm import chat_complete, chat_stream

log = structlog.get_logger()

SYSTEM_PROMPT = """You are an expert FIFA World Cup analyst with deep knowledge of football
statistics, team tactics, and tournament history. You have access to real statistical data
retrieved by specialist agents. Provide clear, insightful, and data-driven analysis.
Be concise but thorough. Use bullet points for clarity. Quote specific statistics."""


def _build_context(state: PlatformState) -> str:
    """Serialise all agent outputs into a structured context block."""
    ctx: Dict[str, Any] = {
        "intent": state.get("intent"),
        "team_codes": state.get("team_codes"),
    }
    codes = state.get("team_codes") or []
    if len(codes) >= 2:
        ctx["home_team"] = codes[0]
        ctx["away_team"] = codes[1]

    team_data = state.get("team_data", {})
    if team_data:
        # Strip _all_teams (too large for context) — use summary instead
        all_teams = team_data.get("_all_teams", [])
        summary_teams = {t["fifa_code"]: t["elo_rating"] for t in all_teams[:10]}
        ctx["team_profiles"] = {k: v for k, v in team_data.items() if k not in ("_all_teams", "head_to_head")}
        ctx["head_to_head"] = team_data.get("head_to_head", [])
        if summary_teams:
            ctx["top_elo_teams"] = summary_teams

    pred = state.get("prediction", {})
    if pred and not pred.get("error"):
        ctx["prediction"] = {k: v for k, v in pred.items() if k != "feature_importances"}

    sim = state.get("sim_results", {})
    if sim and not sim.get("error"):
        ctx["simulation"] = {
            "n_simulations": sim.get("n_simulations"),
            "top_5_favorites": sim.get("top_5_favorites"),
        }

    rag = state.get("rag_docs", [])
    if rag:
        # Use up to 6 docs. With interleaved retrieval these represent at most
        # 2 documents per collection, giving balanced historical/profile/report
        # context without overwhelming the prompt.
        ctx["historical_context"] = rag[:6]

    return json.dumps(ctx, indent=2, default=str)


async def analyst_node(state: PlatformState) -> Dict[str, Any]:
    """LangGraph node — generates state.response via LLM synthesis."""
    t0 = time.monotonic()

    context = _build_context(state)
    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nData context:\n{context}"},
        {"role": "user", "content": state.get("query", "Provide a football analysis.")},
    ]

    response = await chat_complete(messages, temperature=0.4)

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    log.info("analyst_agent.done", response_len=len(response), ms=elapsed)

    return {
        "response": response,
        "trace": [AgentTrace(
            agent="analyst",
            input_keys=["query", "team_data", "prediction", "sim_results", "rag_docs"],
            output_keys=["response"],
            duration_ms=elapsed,
            notes=f"response {len(response)} chars",
        )],
    }


async def analyst_stream(state: PlatformState) -> AsyncIterator[str]:
    """Streaming version of analyst — yields text chunks for SSE."""
    context = _build_context(state)
    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nData context:\n{context}"},
        {"role": "user", "content": state.get("query", "Provide a football analysis.")},
    ]
    async for chunk in chat_stream(messages, temperature=0.4):
        yield chunk

"""OpenAI-compatible LLM client.

If OPENAI_API_KEY is not set, falls back to a deterministic local mode that
generates structured responses from the state — no external API calls needed.
This lets all agent tests run without credentials.
"""

from __future__ import annotations

import json
import re
from typing import Any, AsyncIterator

import structlog

from app.core.config import get_settings

log = structlog.get_logger()
settings = get_settings()

_client = None


def _get_client():
    global _client
    if _client is None and settings.openai_api_key:
        from openai import AsyncOpenAI
        _client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    return _client


async def chat_complete(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.3,
    response_format: dict | None = None,
) -> str:
    """Single non-streaming completion. Falls back to local mode if no API key."""
    client = _get_client()
    if client is None:
        return _local_complete(messages)

    kwargs: dict[str, Any] = dict(
        model=model or settings.openai_model,
        messages=messages,
        temperature=temperature,
    )
    if response_format:
        kwargs["response_format"] = response_format

    resp = await client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


async def chat_stream(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.3,
) -> AsyncIterator[str]:
    """Streaming completion. Falls back to local mode if no API key."""
    client = _get_client()
    if client is None:
        text = _local_complete(messages)
        for chunk in _chunk(text, size=40):
            yield chunk
        return

    stream = await client.chat.completions.create(
        model=model or settings.openai_model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    async for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield delta


# ── Local (no-LLM) fallback ────────────────────────────────────────────────

def _local_complete(messages: list[dict[str, str]]) -> str:
    """Deterministic response derived from the last user message."""
    last_user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    # Extract JSON payload embedded in system messages (used by agents)
    system_data = {}
    for m in messages:
        if m["role"] == "system":
            try:
                match = re.search(r"\{.*\}", m["content"], re.DOTALL)
                if match:
                    system_data = json.loads(match.group())
            except Exception:
                pass

    # Prefer the orchestrator's intent (present in the analyst context);
    # keyword matching on the raw message is only a fallback.
    intent = system_data.get("intent", "")
    lower = last_user.lower()
    # Only render a specialised template when its agent actually produced
    # data — otherwise it would print placeholder numbers ("Home team vs
    # Away team", 40%/25%/35%) that look like real output.
    if intent == "predict" or "predict" in lower or "prediction" in lower:
        if system_data.get("prediction"):
            return _format_prediction_text(system_data)
    if intent == "simulate" or "simulat" in lower:
        if system_data.get("simulation") or system_data.get("sim_results"):
            return _format_simulation_text(system_data)
    if intent == "analyze" or "analyz" in lower or "analys" in lower:
        return _format_analysis_text(system_data)
    return _format_generic_text(system_data, last_user)


def _format_generic_text(data: dict, query: str) -> str:
    """Readable fallback for lookup/chat intents — never dump raw context."""
    lines = ["Here is what the FIFA 2026 intelligence agents found:"]

    teams = data.get("team_codes") or []
    if teams:
        lines.append(f"\n**Teams in scope:** {', '.join(teams)}")

    top_elo = data.get("top_elo_teams") or {}
    if top_elo:
        ranked = sorted(top_elo.items(), key=lambda x: x[1], reverse=True)[:5]
        lines.append("\n**Top teams by ELO rating:**")
        lines.extend(f"  {i+1}. {code}: {elo:.0f}" for i, (code, elo) in enumerate(ranked))

    h2h = data.get("head_to_head") or []
    if h2h:
        lines.append(f"\n**Head-to-head record:** {len(h2h)} prior meeting(s) on file.")

    docs = data.get("historical_context") or []
    if docs:
        lines.append(f"\n**Historical context:** {docs[0]}")

    if len(lines) == 1:
        return (
            "I don't have specific data for that query yet — try asking for a "
            "match prediction (e.g. 'Predict BRA vs ARG'), a tournament "
            "simulation, or a team analysis."
        )
    return "\n".join(lines)


def _format_prediction_text(data: dict) -> str:
    pred = data.get("prediction", {})
    home = data.get("home_team", "Home team")
    away = data.get("away_team", "Away team")
    hw = pred.get("home_win_prob", 0.4)
    dp = pred.get("draw_prob", 0.25)
    aw = pred.get("away_win_prob", 0.35)
    conf = pred.get("confidence", 0.7)
    return (
        f"**Match Prediction: {home} vs {away}**\n\n"
        f"Win probabilities — {home}: {hw:.1%}  Draw: {dp:.1%}  {away}: {aw:.1%}\n\n"
        f"Confidence: {conf:.0%}\n\n"
        f"The model favours {'a draw' if dp > hw and dp > aw else home if hw >= aw else away} "
        f"based on ELO ratings and recent form. "
        f"Expected goals: {pred.get('expected_home_goals', 1.4):.1f} – "
        f"{pred.get('expected_away_goals', 1.1):.1f}."
    )


def _format_simulation_text(data: dict) -> str:
    # The analyst context nests this under "simulation"; raw state uses "sim_results".
    results = data.get("simulation") or data.get("sim_results") or {}
    top = results.get("top_5_favorites") or sorted(
        results.get("win_probabilities", {}).items(), key=lambda x: x[1], reverse=True
    )[:5]
    lines = "\n".join(f"  {i+1}. {code}: {prob:.1%}" for i, (code, prob) in enumerate(top))
    return (
        f"**FIFA 2026 Tournament Simulation** ({results.get('n_simulations', 0):,} runs)\n\n"
        f"Top title contenders:\n{lines}\n\n"
        "These probabilities reflect each team's ELO strength and expected "
        "performance through the group stage and knockout rounds."
    )


def _format_analysis_text(data: dict) -> str:
    team = data.get("team_codes", ["the team"])[0] if data.get("team_codes") else "the team"
    return (
        f"**Team Analysis: {team}**\n\n"
        "Based on historical performance, current ELO rating, and recent form, "
        f"{team} presents a competitive profile with notable strengths in their "
        "qualifying campaign. For a full breakdown, the Stats Agent has retrieved "
        "head-to-head records and the Research Agent has surfaced relevant "
        "World Cup history."
    )


def _chunk(text: str, size: int) -> list[str]:
    return [text[i: i + size] for i in range(0, len(text), size)]

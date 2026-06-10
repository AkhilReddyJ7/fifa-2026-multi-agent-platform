"""Research Agent — RAG-based retrieval from ChromaDB knowledge base."""

from __future__ import annotations

import time
from typing import Any, Dict, List

import structlog

from app.agents.state import AgentTrace, PlatformState
from app.agents.tools.rag_tools import (
    search_match_reports,
    search_team_profiles,
    search_wc_history,
)

log = structlog.get_logger()


def _build_query(state: PlatformState) -> str:
    """Derive a search query from state."""
    parts = [state.get("query", "")]
    codes = state.get("team_codes", [])
    if codes:
        parts.append(" ".join(codes))
    intent = state.get("intent", "")
    if intent == "predict":
        parts.append("match prediction head to head history")
    elif intent == "simulate":
        parts.append("World Cup tournament winner favorites")
    elif intent == "analyze":
        parts.append("team analysis tactical style performance")
    return " ".join(p for p in parts if p)


async def research_node(state: PlatformState) -> Dict[str, Any]:
    """LangGraph node — populates state.rag_docs with relevant document chunks."""
    t0 = time.monotonic()
    query = _build_query(state)

    docs: List[str] = []

    # Search all three collections; deduplicate
    seen: set[str] = set()
    for fetcher, n in [
        (search_wc_history, 4),
        (search_team_profiles, 2),
        (search_match_reports, 2),
    ]:
        for doc in fetcher(query, n_results=n):  # type: ignore[operator]
            key = doc[:80]
            if key not in seen and doc.strip():
                seen.add(key)
                docs.append(doc)

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    log.info("research_agent.done", query=query[:60], docs=len(docs), ms=elapsed)

    return {
        "rag_docs": docs,
        "trace": [AgentTrace(
            agent="research",
            input_keys=["query", "intent", "team_codes"],
            output_keys=["rag_docs"],
            duration_ms=elapsed,
            notes=f"retrieved {len(docs)} document chunks",
        )],
    }

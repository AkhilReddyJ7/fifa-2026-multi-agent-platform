"""Research Agent — RAG-based retrieval from ChromaDB knowledge base."""

from __future__ import annotations

import hashlib
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


def _build_queries(state: PlatformState) -> Dict[str, str]:
    """Build a collection-specific search query for each ChromaDB collection.

    Each collection has different content (tournament narratives, team identity
    docs, post-match tactical reports), so a single shared query produces
    suboptimal retrieval across all three.
    """
    base = state.get("query", "")
    codes = state.get("team_codes", [])
    team_str = " ".join(codes)
    intent = state.get("intent", "chat")

    # ── wc_history: tournament and match narratives ────────────────────────────
    history_parts = [base]
    if team_str:
        history_parts.append(f"{team_str} World Cup match tournament history")
    if intent == "predict":
        history_parts.append("head to head knockout stage")
    elif intent == "simulate":
        history_parts.append("World Cup champion winner title favorites")
    elif intent == "analyze":
        history_parts.append("tournament performance results")

    # ── team_profiles: squad, style, and identity docs ────────────────────────
    if team_str:
        profile_parts = [f"{team_str} squad tactics formation playing style"]
    else:
        profile_parts = ["tournament teams playing style formation"]
    if intent in ("analyze", "lookup"):
        profile_parts.append("strengths weaknesses key players confederation")
    elif intent == "predict":
        profile_parts.append("form ELO rating offensive defensive record")

    # ── match_reports: post-match tactical analysis ────────────────────────────
    if team_str:
        report_parts = [f"{team_str} match analysis tactical report"]
    else:
        report_parts = ["match analysis tactical performance"]
    if intent == "predict":
        report_parts.append("offensive defensive pressing intensity key battles")
    elif intent == "analyze":
        report_parts.append("tactical breakdown turning point statistics")

    return {
        "wc_history": " ".join(p for p in history_parts if p),
        "team_profiles": " ".join(p for p in profile_parts if p),
        "match_reports": " ".join(p for p in report_parts if p),
    }


def _collection_fetch_sizes(intent: str) -> Dict[str, int]:
    """Return how many results to fetch from each collection for the given intent."""
    if intent == "predict":
        return {"wc_history": 2, "match_reports": 3, "team_profiles": 2}
    if intent in ("analyze", "lookup"):
        return {"team_profiles": 3, "match_reports": 3, "wc_history": 2}
    if intent == "simulate":
        return {"wc_history": 4, "team_profiles": 2, "match_reports": 2}
    # chat / default
    return {"wc_history": 3, "team_profiles": 2, "match_reports": 2}


def _doc_hash(doc: str) -> str:
    return hashlib.md5(doc.encode()).hexdigest()


def _fetch_deduped(fetcher, query: str, n: int, seen: set[str]) -> List[str]:
    """Fetch n results from a collection, skipping docs already seen."""
    results: List[str] = []
    for doc in fetcher(query, n_results=n):
        if not doc.strip():
            continue
        h = _doc_hash(doc)
        if h not in seen:
            seen.add(h)
            results.append(doc)
    return results


def _interleave(collections: List[List[str]]) -> List[str]:
    """Round-robin interleave document lists so the final list draws evenly
    from each collection rather than exhausting one before starting the next.

    Example: [A1,A2], [B1,B2], [C1,C2] → [A1,B1,C1,A2,B2,C2]
    """
    result: List[str] = []
    max_len = max((len(c) for c in collections), default=0)
    for i in range(max_len):
        for col in collections:
            if i < len(col):
                result.append(col[i])
    return result


async def research_node(state: PlatformState) -> Dict[str, Any]:
    """LangGraph node — populates state.rag_docs with relevant document chunks."""
    t0 = time.monotonic()
    intent = state.get("intent", "chat")
    queries = _build_queries(state)
    sizes = _collection_fetch_sizes(intent)

    seen: set[str] = set()

    # Fetch from each collection using its dedicated query and n, in priority
    # order determined by intent (sizes dict iteration order matches priority).
    history_docs = _fetch_deduped(
        search_wc_history,
        queries["wc_history"],
        sizes["wc_history"],
        seen,
    )
    profile_docs = _fetch_deduped(
        search_team_profiles,
        queries["team_profiles"],
        sizes["team_profiles"],
        seen,
    )
    report_docs = _fetch_deduped(
        search_match_reports,
        queries["match_reports"],
        sizes["match_reports"],
        seen,
    )

    # Interleave so the analyst sees representation from all three collections
    # in the first N documents rather than one collection dominating.
    docs = _interleave([history_docs, profile_docs, report_docs])

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    log.info(
        "research_agent.done",
        query=queries["wc_history"][:60],
        docs=len(docs),
        history=len(history_docs),
        profiles=len(profile_docs),
        reports=len(report_docs),
        ms=elapsed,
    )

    return {
        "rag_docs": docs,
        "trace": [AgentTrace(
            agent="research",
            input_keys=["query", "intent", "team_codes"],
            output_keys=["rag_docs"],
            duration_ms=elapsed,
            notes=f"retrieved {len(docs)} docs: {len(history_docs)} history, {len(profile_docs)} profiles, {len(report_docs)} reports",
        )],
    }

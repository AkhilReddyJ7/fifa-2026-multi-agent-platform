"""ChromaDB retrieval helpers used by the Research Agent."""

from __future__ import annotations

from typing import List

import structlog

from app.core.config import get_settings

log = structlog.get_logger()
settings = get_settings()


def search_wc_history(query: str, n_results: int = 4) -> List[str]:
    """Search the World Cup history ChromaDB collection.

    Returns a list of document strings. Returns empty list if ChromaDB is unavailable.
    """
    try:
        from app.rag.chroma_client import query_documents
        results = query_documents(
            settings.chroma_collection_wc_history,
            query_texts=[query],
            n_results=n_results,
        )
        docs = results.get("documents", [[]])[0]
        return [d for d in docs if d]
    except Exception as exc:
        log.warning("rag.search.failed", query=query, error=str(exc))
        return []


def search_team_profiles(query: str, n_results: int = 3) -> List[str]:
    """Search the team profiles collection."""
    try:
        from app.rag.chroma_client import query_documents
        results = query_documents(
            settings.chroma_collection_team_profiles,
            query_texts=[query],
            n_results=n_results,
        )
        return results.get("documents", [[]])[0]
    except Exception as exc:
        log.warning("rag.team_profiles.failed", error=str(exc))
        return []


def search_match_reports(query: str, n_results: int = 3) -> List[str]:
    """Search match reports collection."""
    try:
        from app.rag.chroma_client import query_documents
        results = query_documents(
            settings.chroma_collection_match_reports,
            query_texts=[query],
            n_results=n_results,
        )
        return results.get("documents", [[]])[0]
    except Exception as exc:
        log.warning("rag.match_reports.failed", error=str(exc))
        return []

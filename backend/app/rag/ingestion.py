"""Ingest FIFA document corpora into ChromaDB collections.

Documents live in app/rag/data/ as JSON arrays with the schema:
    [{"id": str, "text": str, "metadata": {...}}, ...]

Each collection has a defined metadata schema:
    world_cup_history:  {year: int, stage: str, home_code: str, away_code: str}
    team_profiles:      {team_code: str, team_name: str, confederation: str}
    match_reports:      {year: int, stage: str, home_code: str, away_code: str}

Ingestion is synchronous and intended for seed scripts only — do not call
these functions from async API handlers as they will block the event loop.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from app.core.config import get_settings
from app.rag.chroma_client import upsert_documents

log = structlog.get_logger()
settings = get_settings()

_DATA_DIR = Path(__file__).parent / "data"


def _load_docs(filename: str) -> list[dict[str, Any]]:
    """Load and return a document list from a JSON data file."""
    path = _DATA_DIR / filename
    with path.open(encoding="utf-8") as fh:
        docs = json.load(fh)
    if not isinstance(docs, list):
        raise ValueError(f"Expected a JSON array in {filename}, got {type(docs).__name__}")
    return docs


def ingest_wc_history() -> int:
    """Ingest World Cup match history narratives into ChromaDB.

    Returns the number of documents upserted.
    """
    docs = _load_docs("wc_history.json")
    ids = [d["id"] for d in docs]
    texts = [d["text"] for d in docs]
    metas = [d["metadata"] for d in docs]
    upsert_documents(settings.chroma_collection_wc_history, ids=ids, documents=texts, metadatas=metas)
    log.info("rag.ingest.wc_history", collection=settings.chroma_collection_wc_history, count=len(ids))
    return len(ids)


def ingest_team_profiles() -> int:
    """Ingest team profile documents (one per qualified team) into ChromaDB.

    Returns the number of documents upserted.
    """
    docs = _load_docs("team_profiles.json")
    ids = [d["id"] for d in docs]
    texts = [d["text"] for d in docs]
    metas = [d["metadata"] for d in docs]
    upsert_documents(settings.chroma_collection_team_profiles, ids=ids, documents=texts, metadatas=metas)
    log.info("rag.ingest.team_profiles", collection=settings.chroma_collection_team_profiles, count=len(ids))
    return len(ids)


def ingest_match_reports() -> int:
    """Ingest post-match tactical analysis reports into ChromaDB.

    Returns the number of documents upserted.
    """
    docs = _load_docs("match_reports.json")
    ids = [d["id"] for d in docs]
    texts = [d["text"] for d in docs]
    metas = [d["metadata"] for d in docs]
    upsert_documents(settings.chroma_collection_match_reports, ids=ids, documents=texts, metadatas=metas)
    log.info("rag.ingest.match_reports", collection=settings.chroma_collection_match_reports, count=len(ids))
    return len(ids)


def ingest_all() -> dict[str, int]:
    """Ingest all three collections. Returns a summary of counts per collection."""
    return {
        "wc_history": ingest_wc_history(),
        "team_profiles": ingest_team_profiles(),
        "match_reports": ingest_match_reports(),
    }

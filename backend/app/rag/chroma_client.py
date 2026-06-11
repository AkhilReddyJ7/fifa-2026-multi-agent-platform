"""ChromaDB client with lazy connection and collection management."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import structlog

from app.core.config import get_settings

log = structlog.get_logger()
settings = get_settings()


@lru_cache(maxsize=1)
def get_chroma_client():  # type: ignore[return]
    """Return a cached ChromaDB HttpClient.

    Raises RuntimeError if the server is unreachable — callers should handle gracefully.
    """
    import chromadb

    client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
    )
    try:
        client.heartbeat()
        log.info("chroma.connected", host=settings.chroma_host, port=settings.chroma_port)
    except Exception as exc:
        log.warning("chroma.unavailable", error=str(exc))
    return client


_COSINE_METADATA: dict[str, Any] = {"hnsw:space": "cosine"}


def get_or_create_collection(name: str, metadata: dict[str, Any] | None = None):
    """Return a ChromaDB collection, creating it if it doesn't exist.

    Always uses cosine distance so that text embedding comparisons are
    scale-invariant. Callers may pass additional metadata which is merged
    with the cosine setting.
    """
    client = get_chroma_client()
    merged = {**_COSINE_METADATA, **(metadata or {})}
    return client.get_or_create_collection(name=name, metadata=merged)


# ── Public helpers ─────────────────────────────────────────────────────────────

def upsert_documents(collection_name: str, ids: list[str], documents: list[str], metadatas: list[dict] | None = None) -> None:
    col = get_or_create_collection(collection_name)
    col.upsert(ids=ids, documents=documents, metadatas=metadatas or [{} for _ in ids])
    log.info("chroma.upsert", collection=collection_name, count=len(ids))


def query_documents(collection_name: str, query_texts: list[str], n_results: int = 5) -> dict:
    col = get_or_create_collection(collection_name)
    # ChromaDB raises if n_results > number of documents in the index.
    count = col.count()
    if count == 0:
        return {"documents": [[]], "metadatas": [[]], "ids": [[]]}
    safe_n = min(n_results, count)
    return col.query(query_texts=query_texts, n_results=safe_n)

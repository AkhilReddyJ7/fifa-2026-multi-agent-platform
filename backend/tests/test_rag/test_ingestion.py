"""Tests for RAG ingestion functions."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import call, patch

import pytest

from app.rag.ingestion import (
    _DATA_DIR,
    _load_docs,
    ingest_all,
    ingest_match_reports,
    ingest_team_profiles,
    ingest_wc_history,
)


# ── _load_docs ────────────────────────────────────────────────────────────────

def test_load_docs_wc_history():
    docs = _load_docs("wc_history.json")
    assert isinstance(docs, list)
    assert len(docs) >= 20
    for d in docs:
        assert "id" in d
        assert "text" in d
        assert "metadata" in d
        assert len(d["text"]) > 50  # meaningful content, not empty stubs
        meta = d["metadata"]
        assert "year" in meta
        assert "stage" in meta
        assert "home_code" in meta
        assert "away_code" in meta


def test_load_docs_team_profiles():
    docs = _load_docs("team_profiles.json")
    assert isinstance(docs, list)
    assert len(docs) >= 40  # at least 40 of 48 teams
    codes = {d["metadata"]["team_code"] for d in docs}
    # Core World Cup teams must be present
    for expected in ("ARG", "BRA", "FRA", "ENG", "GER", "ESP"):
        assert expected in codes, f"Missing profile for {expected}"
    for d in docs:
        meta = d["metadata"]
        assert "team_code" in meta
        assert "team_name" in meta
        assert "confederation" in meta


def test_load_docs_match_reports():
    docs = _load_docs("match_reports.json")
    assert isinstance(docs, list)
    assert len(docs) >= 14  # all seeded matches
    for d in docs:
        meta = d["metadata"]
        assert "year" in meta
        assert "stage" in meta
        assert "home_code" in meta
        assert "away_code" in meta


def test_load_docs_raises_for_missing_file():
    with pytest.raises(FileNotFoundError):
        _load_docs("nonexistent.json")


def test_document_ids_are_unique_within_collection():
    for filename in ("wc_history.json", "team_profiles.json", "match_reports.json"):
        docs = _load_docs(filename)
        ids = [d["id"] for d in docs]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found in {filename}: {[i for i in ids if ids.count(i) > 1]}"


# ── ingest_* functions ────────────────────────────────────────────────────────

@patch("app.rag.ingestion.upsert_documents")
def test_ingest_wc_history_calls_upsert(mock_upsert):
    count = ingest_wc_history()
    assert mock_upsert.call_count == 1
    args = mock_upsert.call_args
    collection, ids, documents, metadatas = args[0][0], args[1]["ids"], args[1]["documents"], args[1]["metadatas"]
    assert "world_cup" in collection or "history" in collection
    assert len(ids) == len(documents) == len(metadatas)
    assert count == len(ids)


@patch("app.rag.ingestion.upsert_documents")
def test_ingest_team_profiles_calls_upsert(mock_upsert):
    count = ingest_team_profiles()
    assert mock_upsert.call_count == 1
    args = mock_upsert.call_args
    ids = args[1]["ids"]
    documents = args[1]["documents"]
    metadatas = args[1]["metadatas"]
    assert len(ids) == len(documents) == len(metadatas)
    assert count == len(ids)
    assert count >= 40


@patch("app.rag.ingestion.upsert_documents")
def test_ingest_match_reports_calls_upsert(mock_upsert):
    count = ingest_match_reports()
    assert mock_upsert.call_count == 1
    args = mock_upsert.call_args
    ids = args[1]["ids"]
    assert count == len(ids)
    assert count >= 14


@patch("app.rag.ingestion.upsert_documents")
def test_ingest_all_calls_all_three(mock_upsert):
    result = ingest_all()
    assert mock_upsert.call_count == 3
    assert "wc_history" in result
    assert "team_profiles" in result
    assert "match_reports" in result
    assert result["wc_history"] >= 20
    assert result["team_profiles"] >= 40
    assert result["match_reports"] >= 14


# ── Data directory ────────────────────────────────────────────────────────────

def test_data_dir_exists():
    assert _DATA_DIR.is_dir()


def test_all_expected_json_files_present():
    for name in ("wc_history.json", "team_profiles.json", "match_reports.json"):
        assert (_DATA_DIR / name).exists(), f"Missing data file: {name}"

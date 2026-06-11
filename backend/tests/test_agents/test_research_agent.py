"""Tests for the Research Agent — query building, deduplication, interleaving."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.agents.research_agent import (
    _build_queries,
    _collection_fetch_sizes,
    _doc_hash,
    _fetch_deduped,
    _interleave,
    research_node,
)
from app.agents.state import initial_state


# ── _build_queries ────────────────────────────────────────────────────────────

def test_build_queries_returns_three_keys():
    state = initial_state("Predict BRA vs ARG")
    state["intent"] = "predict"
    state["team_codes"] = ["BRA", "ARG"]
    queries = _build_queries(state)
    assert set(queries.keys()) == {"wc_history", "team_profiles", "match_reports"}


def test_build_queries_team_codes_appear_in_profile_query():
    state = initial_state("Analyse Brazil")
    state["intent"] = "analyze"
    state["team_codes"] = ["BRA"]
    queries = _build_queries(state)
    assert "BRA" in queries["team_profiles"]


def test_build_queries_predict_intent_includes_h2h_in_history():
    state = initial_state("Who wins BRA vs ARG?")
    state["intent"] = "predict"
    state["team_codes"] = ["BRA", "ARG"]
    queries = _build_queries(state)
    assert "head" in queries["wc_history"].lower() or "knockout" in queries["wc_history"].lower()


def test_build_queries_simulate_intent_includes_champion_in_history():
    state = initial_state("Simulate the tournament")
    state["intent"] = "simulate"
    state["team_codes"] = []
    queries = _build_queries(state)
    assert "champion" in queries["wc_history"].lower() or "winner" in queries["wc_history"].lower()


def test_build_queries_profile_query_differs_from_history_query():
    state = initial_state("Analyze BRA tactics")
    state["intent"] = "analyze"
    state["team_codes"] = ["BRA"]
    queries = _build_queries(state)
    assert queries["team_profiles"] != queries["wc_history"]


# ── _collection_fetch_sizes ────────────────────────────────────────────────────

@pytest.mark.parametrize("intent,expected_priority_key", [
    ("predict", "match_reports"),
    ("analyze", "team_profiles"),
    ("lookup", "team_profiles"),
    ("simulate", "wc_history"),
    ("chat", "wc_history"),
])
def test_collection_fetch_sizes_highest_for_intent(intent, expected_priority_key):
    sizes = _collection_fetch_sizes(intent)
    assert set(sizes.keys()) == {"wc_history", "team_profiles", "match_reports"}
    max_key = max(sizes, key=lambda k: sizes[k])
    assert max_key == expected_priority_key, (
        f"For intent={intent!r}, expected {expected_priority_key!r} to have "
        f"the highest fetch size, got {max_key!r} (sizes={sizes})"
    )


# ── _doc_hash ─────────────────────────────────────────────────────────────────

def test_doc_hash_same_input_same_output():
    assert _doc_hash("hello") == _doc_hash("hello")


def test_doc_hash_different_inputs_different_hashes():
    assert _doc_hash("doc one") != _doc_hash("doc two")


def test_doc_hash_collision_not_possible_with_prefix_match():
    # Two docs that share their first 80 chars but differ afterward
    a = "A" * 80 + "suffix_alpha"
    b = "A" * 80 + "suffix_beta"
    assert _doc_hash(a) != _doc_hash(b)


# ── _fetch_deduped ────────────────────────────────────────────────────────────

def test_fetch_deduped_skips_already_seen():
    seen: set[str] = set()
    doc = "France won the 2018 World Cup."
    seen.add(_doc_hash(doc))

    def mock_fetcher(query, n_results):
        return [doc, "A different document."]

    result = _fetch_deduped(mock_fetcher, "France", 2, seen)
    assert len(result) == 1
    assert result[0] == "A different document."


def test_fetch_deduped_skips_empty_docs():
    seen: set[str] = set()

    def mock_fetcher(query, n_results):
        return ["  ", "Valid document content."]

    result = _fetch_deduped(mock_fetcher, "query", 2, seen)
    assert result == ["Valid document content."]


def test_fetch_deduped_adds_to_seen_set():
    seen: set[str] = set()

    def mock_fetcher(query, n_results):
        return ["Document A", "Document B"]

    _fetch_deduped(mock_fetcher, "query", 2, seen)
    assert len(seen) == 2


# ── _interleave ───────────────────────────────────────────────────────────────

def test_interleave_round_robin():
    a = ["a1", "a2"]
    b = ["b1", "b2"]
    c = ["c1", "c2"]
    result = _interleave([a, b, c])
    assert result == ["a1", "b1", "c1", "a2", "b2", "c2"]


def test_interleave_unequal_lengths():
    a = ["a1", "a2", "a3"]
    b = ["b1"]
    result = _interleave([a, b])
    assert result == ["a1", "b1", "a2", "a3"]


def test_interleave_empty_collection():
    result = _interleave([[], ["b1", "b2"], ["c1"]])
    assert result == ["b1", "c1", "b2"]


def test_interleave_all_empty():
    assert _interleave([[], [], []]) == []


# ── research_node integration ─────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.agents.research_agent.search_wc_history", return_value=["History doc 1", "History doc 2"])
@patch("app.agents.research_agent.search_team_profiles", return_value=["Profile doc 1"])
@patch("app.agents.research_agent.search_match_reports", return_value=["Report doc 1", "Report doc 2"])
async def test_research_node_interleaves_results(mock_reports, mock_profiles, mock_history):
    state = initial_state("Predict BRA vs ARG")
    state["intent"] = "predict"
    state["team_codes"] = ["BRA", "ARG"]

    result = await research_node(state)

    rag_docs = result["rag_docs"]
    # With interleaving: [History1, Profile1, Report1, History2, Report2]
    assert len(rag_docs) == 5
    assert rag_docs[0] == "History doc 1"
    assert rag_docs[1] == "Profile doc 1"
    assert rag_docs[2] == "Report doc 1"


@pytest.mark.asyncio
@patch("app.agents.research_agent.search_wc_history", return_value=[])
@patch("app.agents.research_agent.search_team_profiles", return_value=[])
@patch("app.agents.research_agent.search_match_reports", return_value=[])
async def test_research_node_returns_empty_when_chroma_unavailable(mock_reports, mock_profiles, mock_history):
    state = initial_state("Predict BRA vs ARG")
    state["intent"] = "predict"
    state["team_codes"] = ["BRA", "ARG"]

    result = await research_node(state)

    assert result["rag_docs"] == []
    assert len(result["trace"]) == 1
    assert result["trace"][0]["agent"] == "research"


@pytest.mark.asyncio
@patch("app.agents.research_agent.search_wc_history", return_value=["Doc A", "Doc A"])
@patch("app.agents.research_agent.search_team_profiles", return_value=["Doc A"])
@patch("app.agents.research_agent.search_match_reports", return_value=["Doc B"])
async def test_research_node_deduplicates_across_collections(mock_reports, mock_profiles, mock_history):
    state = initial_state("Analyse team")
    state["intent"] = "analyze"
    state["team_codes"] = ["BRA"]

    result = await research_node(state)

    # "Doc A" appears 3 times across collections but should be included only once
    docs = result["rag_docs"]
    assert docs.count("Doc A") == 1
    assert "Doc B" in docs


@pytest.mark.asyncio
@patch("app.agents.research_agent.search_wc_history", return_value=["H1"])
@patch("app.agents.research_agent.search_team_profiles", return_value=["P1"])
@patch("app.agents.research_agent.search_match_reports", return_value=["R1"])
async def test_research_node_trace_entry_populated(mock_reports, mock_profiles, mock_history):
    state = initial_state("Tell me about France")
    state["intent"] = "chat"
    state["team_codes"] = ["FRA"]

    result = await research_node(state)

    trace = result["trace"]
    assert len(trace) == 1
    entry = trace[0]
    assert entry["agent"] == "research"
    assert entry["duration_ms"] >= 0
    assert "3" in entry["notes"]  # 3 total docs retrieved

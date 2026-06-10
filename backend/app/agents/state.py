"""Shared LangGraph state for the FIFA 2026 agent platform."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional

from typing_extensions import TypedDict


class AgentTrace(TypedDict):
    agent: str
    input_keys: List[str]
    output_keys: List[str]
    duration_ms: float
    notes: str


class PlatformState(TypedDict):
    # ── Input ─────────────────────────────────────────────────────────────────
    query: str
    intent: str                         # predict | simulate | analyze | lookup | chat
    team_codes: List[str]               # extracted team codes e.g. ["BRA", "ARG"]

    # ── Agent outputs (written by specialist nodes) ───────────────────────────
    team_data: Dict[str, Any]           # Stats Agent → raw team stats + h2h
    prediction: Dict[str, Any]          # Prediction Agent → probs, expected goals, XAI
    sim_results: Dict[str, Any]         # Simulation Agent → win probabilities, bracket
    rag_docs: List[str]                 # Research Agent → retrieved document chunks

    # ── Final ─────────────────────────────────────────────────────────────────
    response: str                       # Analyst Agent → human-readable answer
    error: Optional[str]

    # Trace accumulates across all nodes (operator.add merges lists)
    trace: Annotated[List[AgentTrace], operator.add]


def initial_state(query: str) -> PlatformState:
    return PlatformState(
        query=query,
        intent="",
        team_codes=[],
        team_data={},
        prediction={},
        sim_results={},
        rag_docs=[],
        response="",
        error=None,
        trace=[],
    )

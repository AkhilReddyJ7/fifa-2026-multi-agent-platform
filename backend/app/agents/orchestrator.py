"""LangGraph orchestrator — routes queries through the agent pipeline.

Graph topology (intent-based routing):

  START → orchestrator → stats ──────────────────────────────→ analyst → END
                        ↓                                    ↑
                        → prediction (if predict intent) ───┘
                        → simulation (if simulate intent) ──┘
                        → research ─────────────────────────┘

All paths converge at analyst.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict

import structlog
from langgraph.graph import END, START, StateGraph

from app.agents.analyst_agent import analyst_node
from app.agents.prediction_agent import prediction_node
from app.agents.research_agent import research_node
from app.agents.simulation_agent import simulation_node
from app.agents.state import AgentTrace, PlatformState, initial_state
from app.agents.stats_agent import stats_node

log = structlog.get_logger()

# ── Intent classifier ─────────────────────────────────────────────────────────

_PREDICT_RE = re.compile(
    r"\b(predict|vs|versus|who wins?|chance|probability|odds|beat)\b", re.I
)
_SIMULATE_RE = re.compile(
    r"\b(simulat|tournament|bracket|champion|world cup winner|title)\b", re.I
)
_ANALYZE_RE = re.compile(
    r"\b(analyz|analys|profile|strength|weakness|tactic|form|squad)\b", re.I
)
_LOOKUP_RE = re.compile(
    r"\b(stats|statistics|record|history|h2h|head.to.head|played)\b", re.I
)

_TEAM_CODES_RE = re.compile(r"\b([A-Z]{2,3})\b")

# All 48 FIFA 2026 World Cup qualified teams.
# Kept in sync with scripts/seed_data.py TEAMS list.
_KNOWN_CODES = {
    # UEFA (16)
    "AUT", "BEL", "CRO", "DEN", "ENG", "ESP", "FRA", "GER",
    "ITA", "NED", "POL", "POR", "SRB", "SUI", "TUR", "UKR",
    # CONMEBOL (6)
    "ARG", "BRA", "CHL", "COL", "ECU", "URU",
    # CONCACAF (6)
    "CAN", "CRC", "JAM", "MEX", "PAN", "USA",
    # CAF (9)
    "CMR", "CIV", "EGY", "GHA", "MAR", "NGA", "RSA", "SEN", "TUN",
    # AFC (8)
    "AUS", "IDN", "IRN", "IRQ", "JPN", "KOR", "KSA", "QAT",
    # OFC (1)
    "NZL",
    # Inter-confederation (2)
    "UAE", "VEN",
}


def _classify_intent(query: str) -> str:
    if _PREDICT_RE.search(query):
        return "predict"
    if _SIMULATE_RE.search(query):
        return "simulate"
    if _ANALYZE_RE.search(query):
        return "analyze"
    if _LOOKUP_RE.search(query):
        return "lookup"
    return "chat"


def _extract_teams(query: str) -> list[str]:
    matches = _TEAM_CODES_RE.findall(query.upper())
    return [m for m in matches if m in _KNOWN_CODES]


# ── Orchestrator node ─────────────────────────────────────────────────────────

async def orchestrator_node(state: PlatformState) -> Dict[str, Any]:
    """Classify intent and extract team codes from the query."""
    t0 = time.monotonic()
    query = state.get("query", "")
    intent = _classify_intent(query)
    teams = _extract_teams(query)

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    log.info("orchestrator.routed", intent=intent, teams=teams)

    return {
        "intent": intent,
        "team_codes": teams,
        "trace": [AgentTrace(
            agent="orchestrator",
            input_keys=["query"],
            output_keys=["intent", "team_codes"],
            duration_ms=elapsed,
            notes=f"intent={intent}, teams={teams}",
        )],
    }


# ── Routing edges ─────────────────────────────────────────────────────────────

def _route_after_stats(state: PlatformState) -> str:
    """After stats, decide next specialised node or skip to research."""
    intent = state.get("intent", "chat")
    if intent == "predict" and len(state.get("team_codes", [])) >= 2:
        return "prediction"
    if intent == "simulate":
        return "simulation"
    return "research"


def _route_after_prediction_or_simulation(state: PlatformState) -> str:
    return "research"


# ── Graph construction ────────────────────────────────────────────────────────

def build_graph() -> Any:
    """Compile the LangGraph StateGraph."""
    g: StateGraph = StateGraph(PlatformState)

    g.add_node("orchestrator", orchestrator_node)
    g.add_node("stats", stats_node)
    # Node name must differ from the "prediction" state key — LangGraph
    # rejects nodes that shadow state channels.
    g.add_node("prediction_agent", prediction_node)
    g.add_node("simulation", simulation_node)
    g.add_node("research", research_node)
    g.add_node("analyst", analyst_node)

    g.add_edge(START, "orchestrator")
    g.add_edge("orchestrator", "stats")

    g.add_conditional_edges(
        "stats",
        _route_after_stats,
        {"prediction": "prediction_agent", "simulation": "simulation", "research": "research"},
    )

    g.add_edge("prediction_agent", "research")
    g.add_edge("simulation", "research")
    g.add_edge("research", "analyst")
    g.add_edge("analyst", END)

    return g.compile()


# ── Public entry point ────────────────────────────────────────────────────────

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_query(query: str, extra_state: Dict[str, Any] | None = None) -> PlatformState:
    """Run a query through the full agent pipeline and return the final state."""
    state = initial_state(query)
    if extra_state:
        state.update(extra_state)  # type: ignore[typeddict-item]
    graph = _get_graph()
    result: PlatformState = await graph.ainvoke(state)
    return result

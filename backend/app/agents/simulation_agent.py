"""Simulation Agent — Monte Carlo FIFA 2026 tournament simulator."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List

import structlog

from app.agents.state import AgentTrace, PlatformState
from app.ml.simulator import TeamEntry, run_simulation

log = structlog.get_logger()

DEFAULT_SIMULATIONS = 1000
MAX_SIMULATIONS = 10000


async def simulation_node(state: PlatformState) -> Dict[str, Any]:
    """LangGraph node — populates state.sim_results."""
    t0 = time.monotonic()
    team_data = state.get("team_data", {})

    # Extract simulation parameters from query if present
    params = state.get("sim_results", {}).get("_params", {})
    n_sims = min(int(params.get("n_simulations", DEFAULT_SIMULATIONS)), MAX_SIMULATIONS)
    seed = params.get("seed")

    # Build team list from _all_teams or individual team entries
    all_teams_raw: List[Dict[str, Any]] = team_data.get("_all_teams", [])
    if not all_teams_raw:
        # Fall back to individual teams in state
        all_teams_raw = [v for k, v in team_data.items() if k not in ("head_to_head", "_all_teams") and isinstance(v, dict)]

    teams: List[TeamEntry] = [
        TeamEntry(
            code=t["fifa_code"],
            name=t["name"],
            elo=float(t.get("elo_rating") or 1500.0),
            group=t.get("group_label"),
        )
        for t in all_teams_raw
        if t.get("fifa_code") and t.get("name")
    ]

    if not teams:
        elapsed = round((time.monotonic() - t0) * 1000, 1)
        return {
            "sim_results": {"error": "No team data available for simulation."},
            "trace": [AgentTrace(
                agent="simulation",
                input_keys=["team_data"],
                output_keys=["sim_results"],
                duration_ms=elapsed,
                notes="skipped — no teams",
            )],
        }

    result = await asyncio.to_thread(run_simulation, teams=teams, n_simulations=n_sims, seed=seed)

    sim_out = {
        "n_simulations": result.n_simulations,
        "win_probabilities": result.win_probabilities,
        "final_probabilities": result.final_probabilities,
        "semifinal_probabilities": result.semifinal_probabilities,
        "expected_bracket": result.expected_bracket,
        "top_5_favorites": list(result.win_probabilities.items())[:5],
        "params": result.params,
    }

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    log.info(
        "simulation_agent.done",
        teams=len(teams),
        n_sims=n_sims,
        top=list(result.win_probabilities.items())[:3],
        ms=elapsed,
    )

    return {
        "sim_results": sim_out,
        "trace": [AgentTrace(
            agent="simulation",
            input_keys=["team_data"],
            output_keys=["sim_results"],
            duration_ms=elapsed,
            notes=f"{len(teams)} teams, {n_sims} simulations",
        )],
    }

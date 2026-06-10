"""Tournament simulation API endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.orchestrator import run_query

router = APIRouter()


class SimulationRequest(BaseModel):
    n_simulations: int = Field(1000, ge=100, le=10000, description="Number of Monte Carlo runs")
    seed: int | None = Field(None, description="Random seed for reproducibility")


class SimulationResponse(BaseModel):
    run_uuid: str
    n_simulations: int
    win_probabilities: dict
    final_probabilities: dict
    semifinal_probabilities: dict
    top_5_favorites: list
    expected_bracket: dict
    analyst_summary: str
    agent_trace: list


@router.post("", response_model=SimulationResponse, summary="Simulate the FIFA 2026 tournament")
async def run_simulation(payload: SimulationRequest) -> SimulationResponse:
    query = f"Simulate the FIFA 2026 World Cup tournament with {payload.n_simulations} simulations."
    extra = {
        "sim_results": {
            "_params": {
                "n_simulations": payload.n_simulations,
                "seed": payload.seed,
            }
        }
    }
    final_state = await run_query(query, extra_state=extra)
    sim = final_state.get("sim_results", {})

    return SimulationResponse(
        run_uuid=str(uuid.uuid4()),
        n_simulations=sim.get("n_simulations", 0),
        win_probabilities=sim.get("win_probabilities", {}),
        final_probabilities=sim.get("final_probabilities", {}),
        semifinal_probabilities=sim.get("semifinal_probabilities", {}),
        top_5_favorites=sim.get("top_5_favorites", []),
        expected_bracket=sim.get("expected_bracket", {}),
        analyst_summary=final_state.get("response", ""),
        agent_trace=final_state.get("trace", []),
    )

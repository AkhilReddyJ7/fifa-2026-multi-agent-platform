"""Tournament simulation API endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_query
from app.api.deps import get_db
from app.db.models import SimulationRun
from app.schemas.simulations import SimulationRead, SimulationRequest, SimulationResponse

router = APIRouter()


@router.post("", response_model=SimulationResponse, summary="Simulate the FIFA 2026 tournament")
async def run_simulation(
    payload: SimulationRequest,
    db: AsyncSession = Depends(get_db),
) -> SimulationResponse:
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

    run_uuid = str(uuid.uuid4())
    row = SimulationRun(
        run_uuid=run_uuid,
        n_simulations=sim.get("n_simulations", payload.n_simulations),
        params={"n_simulations": payload.n_simulations, "seed": payload.seed},
        win_probabilities=sim.get("win_probabilities", {}),
        final_probabilities=sim.get("final_probabilities", {}),
        semifinal_probabilities=sim.get("semifinal_probabilities", {}),
        top_5_favorites=sim.get("top_5_favorites", []),
        bracket=sim.get("expected_bracket", {}),
        analyst_summary=final_state.get("response", ""),
    )
    db.add(row)
    await db.flush()

    return SimulationResponse(
        id=row.id,
        run_uuid=run_uuid,
        n_simulations=sim.get("n_simulations", 0),
        win_probabilities=sim.get("win_probabilities", {}),
        final_probabilities=sim.get("final_probabilities", {}),
        semifinal_probabilities=sim.get("semifinal_probabilities", {}),
        top_5_favorites=sim.get("top_5_favorites", []),
        expected_bracket=sim.get("expected_bracket", {}),
        analyst_summary=final_state.get("response", ""),
        agent_trace=final_state.get("trace", []),
    )


@router.get("/{run_uuid}", response_model=SimulationRead, summary="Get a saved simulation run by UUID")
async def get_simulation(
    run_uuid: str,
    db: AsyncSession = Depends(get_db),
) -> SimulationRead:
    result = await db.execute(select(SimulationRun).where(SimulationRun.run_uuid == run_uuid))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_uuid}' not found.",
        )
    return SimulationRead.model_validate(row)

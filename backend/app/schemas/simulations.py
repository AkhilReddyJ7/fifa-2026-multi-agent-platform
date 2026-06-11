"""Pydantic schemas for tournament simulations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class SimulationRequest(BaseModel):
    n_simulations: int = Field(1000, ge=100, le=10000, description="Number of Monte Carlo runs")
    seed: int | None = Field(None, description="Random seed for reproducibility")


class SimulationResponse(BaseModel):
    id: int
    run_uuid: str
    n_simulations: int
    win_probabilities: dict
    final_probabilities: dict
    semifinal_probabilities: dict
    top_5_favorites: list
    expected_bracket: dict
    analyst_summary: str
    agent_trace: list


class SimulationRead(BaseModel):
    id: int
    run_uuid: str
    n_simulations: int
    win_probabilities: dict | None = None
    final_probabilities: dict | None = None
    semifinal_probabilities: dict | None = None
    top_5_favorites: list | None = None
    # DB column is `bracket`; expose as `expected_bracket` to match SimulationResponse
    expected_bracket: dict | None = Field(None, validation_alias="bracket")
    analyst_summary: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

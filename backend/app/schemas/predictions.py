"""Pydantic schemas for match predictions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    home_team: str = Field(..., description="Home team FIFA code (e.g. BRA)")
    away_team: str = Field(..., description="Away team FIFA code (e.g. ARG)")
    stage: str = Field("group", description="Match stage: group | r16 | qf | sf | final")


class PredictionResponse(BaseModel):
    id: int
    home_team: str
    away_team: str
    home_code: str
    away_code: str
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    expected_home_goals: float
    expected_away_goals: float
    confidence: float
    model_version: str
    explainability: str
    analyst_summary: str
    agent_trace: list


class PredictionRead(BaseModel):
    id: int
    home_team_code: str | None = None
    away_team_code: str | None = None
    stage: str | None = None
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    predicted_home_goals: float | None = None
    predicted_away_goals: float | None = None
    confidence: float | None = None
    model_version: str
    explainability: str | None = None
    analyst_summary: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}

"""Match prediction API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_query
from app.api.deps import get_db
from app.agents.tools.db_tools import get_team_by_code

router = APIRouter()


class PredictionRequest(BaseModel):
    home_team: str = Field(..., description="Home team FIFA code (e.g. BRA)")
    away_team: str = Field(..., description="Away team FIFA code (e.g. ARG)")
    stage: str = Field("group", description="Match stage: group | r16 | qf | sf | final")


class PredictionResponse(BaseModel):
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


@router.post("", response_model=PredictionResponse, summary="Predict a match outcome")
async def predict_match(
    payload: PredictionRequest,
    db: AsyncSession = Depends(get_db),
) -> PredictionResponse:
    home = payload.home_team.upper()
    away = payload.away_team.upper()

    for code in [home, away]:
        team = await get_team_by_code(db, code)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team '{code}' not found in database.",
            )

    query = f"Predict the match {home} vs {away} in the {payload.stage} stage."
    final_state = await run_query(query)

    pred = final_state.get("prediction", {})
    if pred.get("error"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=pred["error"])

    return PredictionResponse(
        home_team=pred.get("home_team", home),
        away_team=pred.get("away_team", away),
        home_code=pred.get("home_code", home),
        away_code=pred.get("away_code", away),
        home_win_prob=pred.get("home_win_prob", 0.0),
        draw_prob=pred.get("draw_prob", 0.0),
        away_win_prob=pred.get("away_win_prob", 0.0),
        expected_home_goals=pred.get("expected_home_goals", 0.0),
        expected_away_goals=pred.get("expected_away_goals", 0.0),
        confidence=pred.get("confidence", 0.0),
        model_version=pred.get("model_version", "unknown"),
        explainability=pred.get("explainability", ""),
        analyst_summary=final_state.get("response", ""),
        agent_trace=final_state.get("trace", []),
    )

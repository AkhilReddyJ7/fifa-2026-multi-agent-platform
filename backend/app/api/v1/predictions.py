"""Match prediction API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_query
from app.agents.tools.db_tools import get_team_by_code
from app.api.deps import get_db
from app.db.models import Prediction
from app.schemas.predictions import PredictionRead, PredictionRequest, PredictionResponse

router = APIRouter()


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

    home_team_code = pred.get("home_code", home)
    away_team_code = pred.get("away_code", away)
    home_win_prob = pred.get("home_win_prob", 0.0)
    draw_prob = pred.get("draw_prob", 0.0)
    away_win_prob = pred.get("away_win_prob", 0.0)
    predicted_home_goals = pred.get("expected_home_goals")
    predicted_away_goals = pred.get("expected_away_goals")
    confidence = pred.get("confidence")
    model_version = pred.get("model_version", "v1")
    explainability = pred.get("explainability") or None
    analyst_summary = final_state.get("response") or None

    row = Prediction(
        home_team_code=home_team_code,
        away_team_code=away_team_code,
        stage=payload.stage,
        home_win_prob=home_win_prob,
        draw_prob=draw_prob,
        away_win_prob=away_win_prob,
        predicted_home_goals=predicted_home_goals,
        predicted_away_goals=predicted_away_goals,
        confidence=confidence,
        model_version=model_version,
        explainability=explainability,
        analyst_summary=analyst_summary,
    )
    try:
        db.add(row)
        await db.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Prediction conflicts with an existing record.",
        )

    return PredictionResponse(
        id=row.id,
        home_team=pred.get("home_team", home),
        away_team=pred.get("away_team", away),
        home_team_code=home_team_code,
        away_team_code=away_team_code,
        home_win_prob=home_win_prob,
        draw_prob=draw_prob,
        away_win_prob=away_win_prob,
        predicted_home_goals=predicted_home_goals,
        predicted_away_goals=predicted_away_goals,
        confidence=confidence,
        model_version=model_version,
        explainability=explainability,
        analyst_summary=analyst_summary,
        agent_trace=final_state.get("trace", []),
    )


@router.get("/{prediction_id}", response_model=PredictionRead, summary="Get a saved prediction by ID")
async def get_prediction(
    prediction_id: int,
    db: AsyncSession = Depends(get_db),
) -> PredictionRead:
    result = await db.execute(select(Prediction).where(Prediction.id == prediction_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction {prediction_id} not found.",
        )
    return PredictionRead.model_validate(row)

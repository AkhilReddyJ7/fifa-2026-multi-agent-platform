"""Prediction Agent — ELO-based match prediction with explainability."""

from __future__ import annotations

import time
from typing import Any, Dict

import structlog

from app.agents.state import AgentTrace, PlatformState
from app.ml.predictor import MatchPrediction, predict_match

log = structlog.get_logger()


def _extract_elo(team_data: Dict[str, Any], code: str, default: float = 1500.0) -> float:
    team = team_data.get(code, {})
    return float(team.get("elo_rating") or default)


def _extract_form(team_data: Dict[str, Any], code: str) -> float | None:
    team = team_data.get(code, {})
    return team.get("form_index")


async def prediction_node(state: PlatformState) -> Dict[str, Any]:
    """LangGraph node — populates state.prediction.

    Expects exactly two teams in state.team_codes.
    Falls back gracefully if team data is missing.
    """
    t0 = time.monotonic()
    team_codes = state.get("team_codes", [])
    team_data = state.get("team_data", {})

    if len(team_codes) < 2:
        elapsed = round((time.monotonic() - t0) * 1000, 1)
        return {
            "prediction": {"error": "Prediction requires exactly two team codes."},
            "trace": [AgentTrace(
                agent="prediction",
                input_keys=["team_codes", "team_data"],
                output_keys=["prediction"],
                duration_ms=elapsed,
                notes="skipped — insufficient teams",
            )],
        }

    home_code, away_code = team_codes[0], team_codes[1]
    home_elo = _extract_elo(team_data, home_code)
    away_elo = _extract_elo(team_data, away_code)
    home_form = _extract_form(team_data, home_code)
    away_form = _extract_form(team_data, away_code)

    # World Cup matches are neutral venue
    pred: MatchPrediction = predict_match(
        home_elo=home_elo,
        away_elo=away_elo,
        home_form=home_form,
        away_form=away_form,
        is_neutral=True,
    )

    home_team_name = team_data.get(home_code, {}).get("name", home_code)
    away_team_name = team_data.get(away_code, {}).get("name", away_code)

    result = {
        "home_team": home_team_name,
        "away_team": away_team_name,
        "home_code": home_code,
        "away_code": away_code,
        "home_win_prob": pred.home_win_prob,
        "draw_prob": pred.draw_prob,
        "away_win_prob": pred.away_win_prob,
        "expected_home_goals": pred.expected_home_goals,
        "expected_away_goals": pred.expected_away_goals,
        "confidence": pred.confidence,
        "model_version": pred.model_version,
        "feature_importances": pred.feature_importances,
        "explainability": _build_xai_narrative(pred, home_team_name, away_team_name),
    }

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    log.info("prediction_agent.done", home=home_code, away=away_code, hw=pred.home_win_prob, ms=elapsed)

    return {
        "prediction": result,
        "trace": [AgentTrace(
            agent="prediction",
            input_keys=["team_codes", "team_data"],
            output_keys=["prediction"],
            duration_ms=elapsed,
            notes=f"{home_code} vs {away_code}: hw={pred.home_win_prob:.2f}",
        )],
    }


def _build_xai_narrative(pred: MatchPrediction, home: str, away: str) -> str:
    fi = pred.feature_importances
    elo_diff = fi.get("elo_diff", 0.0)
    direction = "higher" if elo_diff > 0 else "lower"
    magnitude = abs(elo_diff)

    lines = [
        "**Key factors driving this prediction:**",
        f"- ELO ratings: {home} ({fi.get('home_elo')}) vs {away} ({fi.get('away_elo')}) — "
        f"{home} has {magnitude:.0f} points {direction} ELO.",
    ]

    if abs(fi.get("home_form_modifier", 0)) > 0.05:
        form_dir = "positive" if fi["home_form_modifier"] > 0 else "negative"
        lines.append(f"- {home}'s recent form applies a {form_dir} modifier.")
    if abs(fi.get("away_form_modifier", 0)) > 0.05:
        form_dir = "positive" if fi["away_form_modifier"] > 0 else "negative"
        lines.append(f"- {away}'s recent form applies a {form_dir} modifier.")

    lines.append(
        f"- Model confidence: {pred.confidence:.0%} "
        f"(higher when ELO gap is large)."
    )
    return "\n".join(lines)

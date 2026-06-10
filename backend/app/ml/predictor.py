"""ELO-based match prediction engine.

Uses the ELO rating system (K=32, 400-point scale) to compute win/draw/loss
probabilities and Dixon-Coles-inspired Poisson expected goals.
No external ML libraries required — pure Python + math.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


# Home advantage in ELO points
HOME_ADVANTAGE = 80.0

# Base scoring rate (goals per 90 min for average team)
BASE_LAMBDA = 1.35


@dataclass
class MatchPrediction:
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    expected_home_goals: float
    expected_away_goals: float
    confidence: float
    model_version: str
    feature_importances: Dict[str, float]


def elo_expected(rating_a: float, rating_b: float) -> float:
    """Expected score for team A against team B (0–1)."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def _poisson_pmf(k: int, lam: float) -> float:
    """P(X=k) for Poisson(lam)."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _score_probs(lam_h: float, lam_a: float, max_goals: int = 7) -> Tuple[float, float, float]:
    """Compute win/draw/loss probabilities from Poisson parameters."""
    home_win = draw = away_win = 0.0
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = _poisson_pmf(h, lam_h) * _poisson_pmf(a, lam_a)
            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p
    # Normalise residual (truncation artefact)
    total = home_win + draw + away_win
    return home_win / total, draw / total, away_win / total


def predict_match(
    home_elo: float,
    away_elo: float,
    home_form: Optional[float] = None,
    away_form: Optional[float] = None,
    is_neutral: bool = False,
) -> MatchPrediction:
    """Predict a single match outcome.

    Args:
        home_elo: ELO rating of the home/first team.
        away_elo: ELO rating of the away/second team.
        home_form: rolling form index 0–1 (None = ignore).
        away_form: rolling form index 0–1 (None = ignore).
        is_neutral: True for World Cup games (no home advantage).
    """
    h_adj = home_elo + (0 if is_neutral else HOME_ADVANTAGE)
    a_adj = away_elo

    # Form modifier (±5% of ELO)
    if home_form is not None:
        h_adj += (home_form - 0.5) * 100
    if away_form is not None:
        a_adj += (away_form - 0.5) * 100

    e_h = elo_expected(h_adj, a_adj)   # expected score for home team

    # Map expected score → expected goals via log-odds scaling
    lam_h = BASE_LAMBDA * (e_h / 0.5) ** 0.7
    lam_a = BASE_LAMBDA * ((1 - e_h) / 0.5) ** 0.7

    hw, dr, aw = _score_probs(lam_h, lam_a)

    elo_diff = abs(home_elo - away_elo)
    confidence = min(0.95, 0.5 + elo_diff / 2000.0)

    features = {
        "home_elo": round(home_elo, 1),
        "away_elo": round(away_elo, 1),
        "elo_diff": round(home_elo - away_elo, 1),
        "home_advantage_applied": not is_neutral,
        "home_form_modifier": round((home_form or 0.5) - 0.5, 3),
        "away_form_modifier": round((away_form or 0.5) - 0.5, 3),
        "elo_expected_home": round(e_h, 4),
    }

    return MatchPrediction(
        home_win_prob=round(hw, 4),
        draw_prob=round(dr, 4),
        away_win_prob=round(aw, 4),
        expected_home_goals=round(lam_h, 2),
        expected_away_goals=round(lam_a, 2),
        confidence=round(confidence, 4),
        model_version="elo-poisson-v1",
        feature_importances=features,
    )

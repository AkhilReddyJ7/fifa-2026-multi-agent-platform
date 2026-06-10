"""Async database query helpers used by the Stats Agent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Match, Player, Team, TeamStats

log = structlog.get_logger()


async def get_team_by_code(db: AsyncSession, code: str) -> Optional[Dict[str, Any]]:
    result = await db.execute(select(Team).where(Team.fifa_code == code.upper()))
    team = result.scalar_one_or_none()
    if not team:
        return None
    return {
        "id": team.id,
        "name": team.name,
        "fifa_code": team.fifa_code,
        "confederation": team.confederation,
        "elo_rating": team.elo_rating,
        "form_index": team.form_index,
        "group_label": team.group_label,
    }


async def get_team_players(db: AsyncSession, team_code: str) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(Player)
        .join(Team, Player.team_id == Team.id)
        .where(Team.fifa_code == team_code.upper())
        .order_by(Player.rating.desc().nullslast())
    )
    players = result.scalars().all()
    return [
        {
            "name": p.name,
            "position": p.position,
            "caps": p.caps,
            "goals": p.goals,
            "rating": p.rating,
            "age": p.age,
            "is_captain": p.is_captain,
        }
        for p in players
    ]


async def get_head_to_head(
    db: AsyncSession, code_a: str, code_b: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """Return recent matches between two teams (any order)."""
    q = (
        select(Match)
        .join(Team, Match.home_team_id == Team.id)
        .where(
            (
                (Match.home_team_id == select(Team.id).where(Team.fifa_code == code_a.upper()).scalar_subquery())
                & (Match.away_team_id == select(Team.id).where(Team.fifa_code == code_b.upper()).scalar_subquery())
            )
            | (
                (Match.home_team_id == select(Team.id).where(Team.fifa_code == code_b.upper()).scalar_subquery())
                & (Match.away_team_id == select(Team.id).where(Team.fifa_code == code_a.upper()).scalar_subquery())
            )
        )
        .order_by(Match.tournament_year.desc(), Match.match_date.desc().nullslast())
        .limit(limit)
    )
    results = (await db.execute(q)).scalars().all()

    # Resolve team codes for each match
    out = []
    for m in results:
        home_team = (await db.execute(select(Team).where(Team.id == m.home_team_id))).scalar_one_or_none()
        away_team = (await db.execute(select(Team).where(Team.id == m.away_team_id))).scalar_one_or_none()
        out.append({
            "year": m.tournament_year,
            "stage": m.stage,
            "venue": m.venue,
            "home": home_team.fifa_code if home_team else "?",
            "away": away_team.fifa_code if away_team else "?",
            "home_goals": m.home_goals,
            "away_goals": m.away_goals,
            "home_goals_pen": m.home_goals_pen,
            "away_goals_pen": m.away_goals_pen,
        })
    return out


async def get_team_match_stats(
    db: AsyncSession, team_code: str, limit: int = 10
) -> Dict[str, Any]:
    """Aggregate recent match stats for a team."""
    team_row = await get_team_by_code(db, team_code)
    if not team_row:
        return {}

    team_id = team_row["id"]
    result = await db.execute(
        select(TeamStats)
        .where(TeamStats.team_id == team_id)
        .order_by(TeamStats.id.desc())
        .limit(limit)
    )
    stats = result.scalars().all()
    if not stats:
        return {"team_id": team_id, "matches_with_stats": 0}

    def _avg(attr: str) -> Optional[float]:
        vals = [getattr(s, attr) for s in stats if getattr(s, attr) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    return {
        "team_id": team_id,
        "matches_with_stats": len(stats),
        "avg_possession": _avg("possession"),
        "avg_shots_on_target": _avg("shots_on_target"),
        "avg_xg": _avg("xg"),
        "avg_pass_accuracy": _avg("pass_accuracy"),
    }


async def get_all_teams(db: AsyncSession) -> List[Dict[str, Any]]:
    """Return all teams with their ELO ratings."""
    result = await db.execute(select(Team).order_by(Team.elo_rating.desc().nullslast()))
    teams = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "fifa_code": t.fifa_code,
            "confederation": t.confederation,
            "elo_rating": t.elo_rating or 1500.0,
            "group_label": t.group_label,
        }
        for t in teams
    ]

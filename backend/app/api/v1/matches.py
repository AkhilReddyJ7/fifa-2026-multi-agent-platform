from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.db.models import Match, Team
from app.schemas.matches import MatchCreate, MatchList, MatchRead, TeamStatsRead

router = APIRouter()


def _enrich(match: Match) -> MatchRead:
    data = MatchRead.model_validate(match)
    if match.home_team:
        data.home_team_name = match.home_team.name
        data.home_team_code = match.home_team.fifa_code
    if match.away_team:
        data.away_team_name = match.away_team.name
        data.away_team_code = match.away_team.fifa_code
    return data


_LOAD = [
    selectinload(Match.home_team),
    selectinload(Match.away_team),
    selectinload(Match.stats),
]


@router.get("", response_model=MatchList, summary="List matches")
async def list_matches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    year: Optional[int] = None,
    stage: Optional[str] = None,
    team_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> MatchList:
    query = select(Match).options(*_LOAD)

    if year:
        query = query.where(Match.tournament_year == year)
    if stage:
        query = query.where(Match.stage == stage.lower())
    if team_code:
        sub = select(Team.id).where(Team.fifa_code == team_code.upper())
        team_id = (await db.execute(sub)).scalar_one_or_none()
        if team_id:
            query = query.where((Match.home_team_id == team_id) | (Match.away_team_id == team_id))

    count_q = select(func.count()).select_from(query.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Match.match_date.desc().nullslast())
    matches = (await db.execute(query)).scalars().all()

    return MatchList(
        items=[_enrich(m) for m in matches],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{match_id}", response_model=MatchRead, summary="Get match by ID")
async def get_match(match_id: int, db: AsyncSession = Depends(get_db)) -> MatchRead:
    result = await db.execute(select(Match).options(*_LOAD).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Match {match_id} not found")
    return _enrich(match)


@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED, summary="Create a match record")
async def create_match(payload: MatchCreate, db: AsyncSession = Depends(get_db)) -> MatchRead:
    for team_id, label in [(payload.home_team_id, "home"), (payload.away_team_id, "away")]:
        exists = (await db.execute(select(Team.id).where(Team.id == team_id))).scalar_one_or_none()
        if not exists:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{label}_team_id {team_id} not found")

    match = Match(**payload.model_dump())
    db.add(match)
    await db.flush()

    result = await db.execute(select(Match).options(*_LOAD).where(Match.id == match.id))
    match = result.scalar_one()
    return _enrich(match)


@router.get("/{match_id}/stats", response_model=list[TeamStatsRead], summary="Get per-team stats for a match")
async def get_match_stats(match_id: int, db: AsyncSession = Depends(get_db)) -> list[TeamStatsRead]:
    result = await db.execute(select(Match).options(selectinload(Match.stats)).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Match {match_id} not found")
    return [TeamStatsRead.model_validate(s) for s in match.stats]

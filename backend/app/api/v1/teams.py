from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.db.models import Player, Team
from app.schemas.teams import PlayerCreate, PlayerRead, TeamCreate, TeamList, TeamRead, TeamUpdate

router = APIRouter()


@router.get("", response_model=TeamList, summary="List all teams")
async def list_teams(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    confederation: Optional[str] = None,
    group_label: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> TeamList:
    query = select(Team)
    if confederation:
        query = query.where(Team.confederation == confederation.upper())
    if group_label:
        query = query.where(Team.group_label == group_label.upper())

    count_q = select(func.count()).select_from(query.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Team.name)
    teams = (await db.execute(query)).scalars().all()

    return TeamList(
        items=[TeamRead.model_validate(t) for t in teams],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{fifa_code}", response_model=TeamRead, summary="Get team by FIFA code")
async def get_team(fifa_code: str, db: AsyncSession = Depends(get_db)) -> TeamRead:
    result = await db.execute(
        select(Team).where(Team.fifa_code == fifa_code.upper())
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{fifa_code}' not found")
    return TeamRead.model_validate(team)


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED, summary="Create a team")
async def create_team(payload: TeamCreate, db: AsyncSession = Depends(get_db)) -> TeamRead:
    existing = (await db.execute(select(Team).where(Team.fifa_code == payload.fifa_code.upper()))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Team '{payload.fifa_code}' already exists")
    team = Team(**payload.model_dump())
    team.fifa_code = team.fifa_code.upper()
    db.add(team)
    await db.flush()
    await db.refresh(team)
    return TeamRead.model_validate(team)


@router.patch("/{fifa_code}", response_model=TeamRead, summary="Update a team")
async def update_team(
    fifa_code: str, payload: TeamUpdate, db: AsyncSession = Depends(get_db)
) -> TeamRead:
    result = await db.execute(select(Team).where(Team.fifa_code == fifa_code.upper()))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{fifa_code}' not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(team, field, value)

    await db.flush()
    await db.refresh(team)
    return TeamRead.model_validate(team)


@router.delete("/{fifa_code}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, summary="Delete a team")
async def delete_team(fifa_code: str, db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(select(Team).where(Team.fifa_code == fifa_code.upper()))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{fifa_code}' not found")
    await db.delete(team)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Players sub-resource ──────────────────────────────────────────────────────

@router.get("/{fifa_code}/players", response_model=list[PlayerRead], summary="List players for a team")
async def list_players(fifa_code: str, db: AsyncSession = Depends(get_db)) -> list[PlayerRead]:
    result = await db.execute(
        select(Team).options(selectinload(Team.players)).where(Team.fifa_code == fifa_code.upper())
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{fifa_code}' not found")
    return [PlayerRead.model_validate(p) for p in team.players]


@router.post(
    "/{fifa_code}/players",
    response_model=PlayerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a player to a team",
)
async def add_player(fifa_code: str, payload: PlayerCreate, db: AsyncSession = Depends(get_db)) -> PlayerRead:
    result = await db.execute(select(Team).where(Team.fifa_code == fifa_code.upper()))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{fifa_code}' not found")

    player = Player(**payload.model_dump(), team_id=team.id)
    db.add(player)
    await db.flush()
    await db.refresh(player)
    return PlayerRead.model_validate(player)

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MatchBase(BaseModel):
    home_team_id: int
    away_team_id: int
    tournament_year: int
    stage: str = Field(..., max_length=30)
    group_label: Optional[str] = Field(None, max_length=2)
    match_date: Optional[datetime] = None
    venue: Optional[str] = None
    city: Optional[str] = None


class MatchCreate(MatchBase):
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    attendance: Optional[int] = None


class MatchRead(MatchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    home_goals_aet: Optional[int] = None
    away_goals_aet: Optional[int] = None
    home_goals_pen: Optional[int] = None
    away_goals_pen: Optional[int] = None
    attendance: Optional[int] = None
    created_at: datetime

    # Nested minimal team info resolved at read time
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    home_team_code: Optional[str] = None
    away_team_code: Optional[str] = None


class MatchList(BaseModel):
    items: list[MatchRead]
    total: int
    page: int
    page_size: int


class TeamStatsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    match_id: int
    possession: Optional[float] = None
    shots: Optional[int] = None
    shots_on_target: Optional[int] = None
    xg: Optional[float] = None
    corners: Optional[int] = None
    fouls: Optional[int] = None
    yellow_cards: Optional[int] = None
    red_cards: Optional[int] = None
    pass_accuracy: Optional[float] = None

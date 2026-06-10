from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    fifa_code: str = Field(..., min_length=2, max_length=3)
    confederation: str = Field(..., max_length=10)
    group_label: Optional[str] = Field(None, max_length=2)
    elo_rating: Optional[float] = None
    form_index: Optional[float] = None
    flag_url: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    elo_rating: Optional[float] = None
    form_index: Optional[float] = None
    group_label: Optional[str] = None
    flag_url: Optional[str] = None


class TeamRead(TeamBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class TeamList(BaseModel):
    items: list[TeamRead]
    total: int
    page: int
    page_size: int


# ── Players ───────────────────────────────────────────────────────────────────

class PlayerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    position: str = Field(..., max_length=3)
    shirt_number: Optional[int] = None
    caps: int = 0
    goals: int = 0
    rating: Optional[float] = None
    age: Optional[int] = None
    is_captain: bool = False


class PlayerCreate(PlayerBase):
    pass


class PlayerRead(PlayerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    created_at: datetime

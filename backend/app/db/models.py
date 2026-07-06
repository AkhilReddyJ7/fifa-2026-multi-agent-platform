"""SQLAlchemy ORM models for FIFA 2026 platform."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uuid() -> str:
    return str(uuid.uuid4())


# ── Teams ─────────────────────────────────────────────────────────────────────

class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    fifa_code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False, index=True)
    confederation: Mapped[str] = mapped_column(String(10), nullable=False)  # UEFA, CONMEBOL …
    group_label: Mapped[Optional[str]] = mapped_column(String(2))            # "A" … "L" for WC2026
    elo_rating: Mapped[Optional[float]] = mapped_column(Float)
    form_index: Mapped[Optional[float]] = mapped_column(Float)               # rolling 5-game form
    flag_url: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    players: Mapped[list[Player]] = relationship("Player", back_populates="team", cascade="all, delete-orphan")
    home_matches: Mapped[list[Match]] = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches: Mapped[list[Match]] = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")
    stats: Mapped[list[TeamStats]] = relationship("TeamStats", back_populates="team", cascade="all, delete-orphan")


# ── Players ───────────────────────────────────────────────────────────────────

class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    position: Mapped[str] = mapped_column(String(3))   # GK, DF, MF, FW
    shirt_number: Mapped[Optional[int]] = mapped_column(Integer)
    caps: Mapped[int] = mapped_column(Integer, default=0)
    goals: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[Optional[float]] = mapped_column(Float)
    age: Mapped[Optional[int]] = mapped_column(Integer)
    is_captain: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped[Team] = relationship("Team", back_populates="players")


# ── Matches ───────────────────────────────────────────────────────────────────

class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("home_team_id", "away_team_id", "match_date", "tournament_year", name="uq_match"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    home_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    away_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    tournament_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)   # group, r16, qf, sf, final
    group_label: Mapped[Optional[str]] = mapped_column(String(2))
    match_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    venue: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    home_goals: Mapped[Optional[int]] = mapped_column(Integer)
    away_goals: Mapped[Optional[int]] = mapped_column(Integer)
    home_goals_aet: Mapped[Optional[int]] = mapped_column(Integer)
    away_goals_aet: Mapped[Optional[int]] = mapped_column(Integer)
    home_goals_pen: Mapped[Optional[int]] = mapped_column(Integer)
    away_goals_pen: Mapped[Optional[int]] = mapped_column(Integer)
    attendance: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    home_team: Mapped[Team] = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team: Mapped[Team] = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    stats: Mapped[list[TeamStats]] = relationship("TeamStats", back_populates="match", cascade="all, delete-orphan")
    prediction: Mapped[Optional[Prediction]] = relationship("Prediction", back_populates="match", uselist=False)


# ── Team Stats per Match ──────────────────────────────────────────────────────

class TeamStats(Base):
    __tablename__ = "team_stats"
    __table_args__ = (
        UniqueConstraint("team_id", "match_id", name="uq_team_match_stats"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    possession: Mapped[Optional[float]] = mapped_column(Float)
    shots: Mapped[Optional[int]] = mapped_column(Integer)
    shots_on_target: Mapped[Optional[int]] = mapped_column(Integer)
    xg: Mapped[Optional[float]] = mapped_column(Float)
    corners: Mapped[Optional[int]] = mapped_column(Integer)
    fouls: Mapped[Optional[int]] = mapped_column(Integer)
    yellow_cards: Mapped[Optional[int]] = mapped_column(Integer)
    red_cards: Mapped[Optional[int]] = mapped_column(Integer)
    pass_accuracy: Mapped[Optional[float]] = mapped_column(Float)
    pressing_intensity: Mapped[Optional[float]] = mapped_column(Float)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)

    team: Mapped[Team] = relationship("Team", back_populates="stats")
    match: Mapped[Match] = relationship("Match", back_populates="stats")


# ── Predictions ───────────────────────────────────────────────────────────────

class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    home_win_prob: Mapped[float] = mapped_column(Float, nullable=False)
    draw_prob: Mapped[float] = mapped_column(Float, nullable=False)
    away_win_prob: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_home_goals: Mapped[Optional[float]] = mapped_column(Float)
    predicted_away_goals: Mapped[Optional[float]] = mapped_column(Float)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(30), default="v1")
    shap_values: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    match: Mapped[Match] = relationship("Match", back_populates="prediction")


# ── Tournament Simulation Runs ────────────────────────────────────────────────

class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_uuid: Mapped[str] = mapped_column(String(36), unique=True, default=_uuid, index=True)
    n_simulations: Mapped[int] = mapped_column(Integer, nullable=False)
    params: Mapped[Optional[dict]] = mapped_column(JSON)
    winner_team_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"))
    bracket: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Chat Sessions ─────────────────────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_uuid: Mapped[str] = mapped_column(String(36), unique=True, default=_uuid, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list[ChatMessage]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)   # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    agent_trace: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[ChatSession] = relationship("ChatSession", back_populates="messages")

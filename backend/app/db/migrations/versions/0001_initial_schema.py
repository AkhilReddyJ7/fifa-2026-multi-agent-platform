"""Initial schema — all Phase 1 tables

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("fifa_code", sa.String(3), nullable=False),
        sa.Column("confederation", sa.String(10), nullable=False),
        sa.Column("group_label", sa.String(2)),
        sa.Column("elo_rating", sa.Float()),
        sa.Column("form_index", sa.Float()),
        sa.Column("flag_url", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fifa_code"),
    )
    op.create_index("ix_teams_fifa_code", "teams", ["fifa_code"])

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("position", sa.String(3)),
        sa.Column("shirt_number", sa.Integer()),
        sa.Column("caps", sa.Integer(), default=0),
        sa.Column("goals", sa.Integer(), default=0),
        sa.Column("rating", sa.Float()),
        sa.Column("age", sa.Integer()),
        sa.Column("is_captain", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_players_team_id", "players", ["team_id"])

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("tournament_year", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("group_label", sa.String(2)),
        sa.Column("match_date", sa.DateTime(timezone=True)),
        sa.Column("venue", sa.String(100)),
        sa.Column("city", sa.String(100)),
        sa.Column("home_goals", sa.Integer()),
        sa.Column("away_goals", sa.Integer()),
        sa.Column("home_goals_aet", sa.Integer()),
        sa.Column("away_goals_aet", sa.Integer()),
        sa.Column("home_goals_pen", sa.Integer()),
        sa.Column("away_goals_pen", sa.Integer()),
        sa.Column("attendance", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("home_team_id", "away_team_id", "match_date", "tournament_year", name="uq_match"),
    )
    op.create_index("ix_matches_home_team_id", "matches", ["home_team_id"])
    op.create_index("ix_matches_away_team_id", "matches", ["away_team_id"])
    op.create_index("ix_matches_tournament_year", "matches", ["tournament_year"])

    op.create_table(
        "team_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("possession", sa.Float()),
        sa.Column("shots", sa.Integer()),
        sa.Column("shots_on_target", sa.Integer()),
        sa.Column("xg", sa.Float()),
        sa.Column("corners", sa.Integer()),
        sa.Column("fouls", sa.Integer()),
        sa.Column("yellow_cards", sa.Integer()),
        sa.Column("red_cards", sa.Integer()),
        sa.Column("pass_accuracy", sa.Float()),
        sa.Column("pressing_intensity", sa.Float()),
        sa.Column("extra_data", postgresql.JSON()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "match_id", name="uq_team_match_stats"),
    )

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("home_win_prob", sa.Float(), nullable=False),
        sa.Column("draw_prob", sa.Float(), nullable=False),
        sa.Column("away_win_prob", sa.Float(), nullable=False),
        sa.Column("predicted_home_goals", sa.Float()),
        sa.Column("predicted_away_goals", sa.Float()),
        sa.Column("confidence", sa.Float()),
        sa.Column("model_version", sa.String(30), default="v1"),
        sa.Column("shap_values", postgresql.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id"),
    )

    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_uuid", sa.String(36), nullable=False),
        sa.Column("n_simulations", sa.Integer(), nullable=False),
        sa.Column("params", postgresql.JSON()),
        sa.Column("winner_team_id", sa.Integer(), sa.ForeignKey("teams.id")),
        sa.Column("bracket", postgresql.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_uuid"),
    )
    op.create_index("ix_simulation_runs_run_uuid", "simulation_runs", ["run_uuid"])

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_uuid", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_uuid"),
    )
    op.create_index("ix_chat_sessions_session_uuid", "chat_sessions", ["session_uuid"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("agent_trace", postgresql.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("simulation_runs")
    op.drop_table("predictions")
    op.drop_table("team_stats")
    op.drop_table("matches")
    op.drop_table("players")
    op.drop_table("teams")

"""Phase 3B — prediction and simulation persistence columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-10 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make match_id nullable (predictions can exist without a linked match row)
    op.alter_column("predictions", "match_id", nullable=True)

    # New context columns on predictions
    op.add_column("predictions", sa.Column("home_team_code", sa.String(3), nullable=True))
    op.add_column("predictions", sa.Column("away_team_code", sa.String(3), nullable=True))
    op.add_column("predictions", sa.Column("stage", sa.String(30), nullable=True))
    op.add_column("predictions", sa.Column("explainability", sa.Text(), nullable=True))
    op.add_column("predictions", sa.Column("analyst_summary", sa.Text(), nullable=True))
    op.create_index("ix_predictions_home_team_code", "predictions", ["home_team_code"])
    op.create_index("ix_predictions_away_team_code", "predictions", ["away_team_code"])

    # New probability / result columns on simulation_runs
    op.add_column("simulation_runs", sa.Column("win_probabilities", postgresql.JSON(), nullable=True))
    op.add_column("simulation_runs", sa.Column("final_probabilities", postgresql.JSON(), nullable=True))
    op.add_column("simulation_runs", sa.Column("semifinal_probabilities", postgresql.JSON(), nullable=True))
    op.add_column("simulation_runs", sa.Column("top_5_favorites", postgresql.JSON(), nullable=True))
    op.add_column("simulation_runs", sa.Column("analyst_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("simulation_runs", "analyst_summary")
    op.drop_column("simulation_runs", "top_5_favorites")
    op.drop_column("simulation_runs", "semifinal_probabilities")
    op.drop_column("simulation_runs", "final_probabilities")
    op.drop_column("simulation_runs", "win_probabilities")

    op.drop_index("ix_predictions_away_team_code", "predictions")
    op.drop_index("ix_predictions_home_team_code", "predictions")
    op.drop_column("predictions", "analyst_summary")
    op.drop_column("predictions", "explainability")
    op.drop_column("predictions", "stage")
    op.drop_column("predictions", "away_team_code")
    op.drop_column("predictions", "home_team_code")

    op.alter_column("predictions", "match_id", nullable=False)

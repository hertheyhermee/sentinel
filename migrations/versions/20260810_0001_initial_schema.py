"""initial schema: monitors and check_results

Revision ID: 0001
Revises: None
Create Date: 2026-08-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "monitors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column(
            "interval_seconds", sa.Integer(), nullable=False, server_default="60"
        ),
        sa.Column(
            "expected_status", sa.Integer(), nullable=False, server_default="200"
        ),
        sa.Column("slo_target", sa.Float(), nullable=False, server_default="0.995"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "next_run_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_monitors_due", "monitors", ["is_active", "next_run_at"], unique=False
    )

    op.create_table(
        "check_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("monitor_id", sa.Integer(), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Float(), nullable=True),
        sa.Column("is_up", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["monitor_id"], ["monitors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_check_results_monitor_time",
        "check_results",
        ["monitor_id", "checked_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_check_results_monitor_time", table_name="check_results")
    op.drop_table("check_results")
    op.drop_index("ix_monitors_due", table_name="monitors")
    op.drop_table("monitors")

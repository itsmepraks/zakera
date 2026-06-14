"""Widen model name columns for OpenRouter slugs.

Revision ID: c3a7d9e4b6f1
Revises: b8f5a4c91d22
Create Date: 2026-06-14 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "c3a7d9e4b6f1"
down_revision: str | None = "b8f5a4c91d22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.alter_column(
            "model_name",
            existing_type=sa.String(length=50),
            type_=sa.String(length=160),
            existing_nullable=True,
        )
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column(
            "model_name",
            existing_type=sa.String(length=50),
            type_=sa.String(length=160),
            existing_nullable=True,
        )
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.alter_column(
            "model_name",
            existing_type=sa.String(length=100),
            type_=sa.String(length=160),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.alter_column(
            "model_name",
            existing_type=sa.String(length=160),
            type_=sa.String(length=100),
            existing_nullable=False,
        )
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column(
            "model_name",
            existing_type=sa.String(length=160),
            type_=sa.String(length=50),
            existing_nullable=True,
        )
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.alter_column(
            "model_name",
            existing_type=sa.String(length=160),
            type_=sa.String(length=50),
            existing_nullable=True,
        )

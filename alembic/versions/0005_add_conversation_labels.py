"""Add conversation labels/tags support

Revision ID: 0005_add_conversation_labels
Revises: 0004
Create Date: 2026-03-12 22:00:00.000000

This migration introduces a two-table design for flexible conversation
labelling:

  labels              — lookup table of distinct label values per user
  conversation_labels — many-to-many join between conversations and labels

Usage examples
--------------
  # Tag a conversation as 'work' and 'research'
  INSERT INTO labels (id, user_id, name, color) VALUES (uuid(), 'u1', 'work',     '#3b82f6');
  INSERT INTO labels (id, user_id, name, color) VALUES (uuid(), 'u1', 'research', '#10b981');

  INSERT INTO conversation_labels (conversation_id, label_id) VALUES ('c1', 'l1');
  INSERT INTO conversation_labels (conversation_id, label_id) VALUES ('c1', 'l2');

Indexes
-------
  * labels.user_id         — fast per-user label listing
  * conversation_labels.conversation_id  — fast label lookup per conversation
  * conversation_labels.label_id         — fast conversation lookup per label
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# ---------------------------------------------------------------------------
# Revision identifiers (used by Alembic)
# ---------------------------------------------------------------------------
revision = "0005_add_conversation_labels"
down_revision = "0004"          # adjust to match the actual previous revision id
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. labels — reusable named tags owned by a user
    # ------------------------------------------------------------------
    op.create_table(
        "labels",
        sa.Column("id",         sa.String(36),  nullable=False, primary_key=True),
        sa.Column("user_id",    sa.String(36),  nullable=False),
        sa.Column("name",       sa.String(80),  nullable=False),
        sa.Column(
            "color",
            sa.String(9),
            nullable=False,
            server_default="#6b7280",
            comment="Hex colour string, e.g. #3b82f6",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("user_id", "name", name="uq_labels_user_name"),
    )

    op.create_index(
        "ix_labels_user_id",
        "labels",
        ["user_id"],
    )

    # ------------------------------------------------------------------
    # 2. conversation_labels — many-to-many join table
    # ------------------------------------------------------------------
    op.create_table(
        "conversation_labels",
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("label_id",        sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("conversation_id", "label_id", name="pk_conversation_labels"),
        sa.ForeignKeyConstraint(
            ["label_id"],
            ["labels.id"],
            name="fk_conv_labels_label_id",
            ondelete="CASCADE",
        ),
        # Note: uncomment the FK below once conversations table exists in the
        # migrations history (avoids circular dependency in SQLite tests).
        # sa.ForeignKeyConstraint(
        #     ["conversation_id"],
        #     ["conversations.id"],
        #     name="fk_conv_labels_conversation_id",
        #     ondelete="CASCADE",
        # ),
    )

    op.create_index(
        "ix_conversation_labels_conversation_id",
        "conversation_labels",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_labels_label_id",
        "conversation_labels",
        ["label_id"],
    )


# ---------------------------------------------------------------------------
# Downgrade — fully reversible
# ---------------------------------------------------------------------------

def downgrade() -> None:
    op.drop_index("ix_conversation_labels_label_id",        table_name="conversation_labels")
    op.drop_index("ix_conversation_labels_conversation_id", table_name="conversation_labels")
    op.drop_table("conversation_labels")

    op.drop_index("ix_labels_user_id", table_name="labels")
    op.drop_table("labels")

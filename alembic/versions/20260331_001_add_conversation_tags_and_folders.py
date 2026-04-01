"""Add conversation tags and folders

Revision ID: a7f3c9e21d08
Revises: 0005_add_conversation_labels
Create Date: 2026-03-31 22:00:00.000000

Adds:
- conversation_folders table  (user-owned folders for organizing conversations)
- conversation_tags table     (many-to-many tag library per user)
- conversation_tag_associations table (M2M join between conversations and tags)
- folder_id FK column on the conversations table
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7f3c9e21d08"
down_revision: str | None = "0005_add_conversation_labels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. conversation_folders
    # ------------------------------------------------------------------
    op.create_table(
        "conversation_folders",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "color",
            sa.String(7),
            nullable=False,
            server_default="#6366f1",
            comment="Hex color code for UI display, e.g. #6366f1",
        ),
        sa.Column("icon", sa.String(50), nullable=True, comment="Optional emoji or icon name"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0",
                  comment="Sort order within the user's folder list"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_conversation_folders_user_id", "conversation_folders", ["user_id"])
    op.create_index(
        "ix_conversation_folders_user_position",
        "conversation_folders",
        ["user_id", "position"],
    )

    # ------------------------------------------------------------------
    # 2. conversation_tags  (tag library, one row per unique tag per user)
    # ------------------------------------------------------------------
    op.create_table(
        "conversation_tags",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "color",
            sa.String(7),
            nullable=False,
            server_default="#64748b",
            comment="Hex color code for the tag pill in the UI",
        ),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0",
                  comment="Denormalized count — incremented/decremented by the application layer"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("user_id", "name", name="uq_conversation_tags_user_name"),
    )
    op.create_index("ix_conversation_tags_user_id", "conversation_tags", ["user_id"])

    # ------------------------------------------------------------------
    # 3. conversation_tag_associations  (M2M join table)
    # ------------------------------------------------------------------
    op.create_table(
        "conversation_tag_associations",
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.String(36),
            sa.ForeignKey("conversation_tags.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tagged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_conversation_tag_assoc_conversation",
        "conversation_tag_associations",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_tag_assoc_tag",
        "conversation_tag_associations",
        ["tag_id"],
    )

    # ------------------------------------------------------------------
    # 4. Add folder_id FK to conversations
    # ------------------------------------------------------------------
    op.add_column(
        "conversations",
        sa.Column(
            "folder_id",
            sa.String(36),
            sa.ForeignKey("conversation_folders.id", ondelete="SET NULL"),
            nullable=True,
            comment="Optional folder this conversation belongs to",
        ),
    )
    op.create_index("ix_conversations_folder_id", "conversations", ["folder_id"])

    # ------------------------------------------------------------------
    # 5. Add pinned + archived convenience columns to conversations
    # ------------------------------------------------------------------
    op.add_column(
        "conversations",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="Pinned conversations appear at the top of the list",
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="Archived conversations are hidden from the main list by default",
        ),
    )
    op.create_index(
        "ix_conversations_is_pinned_created_at",
        "conversations",
        ["is_pinned", "created_at"],
    )


def downgrade() -> None:
    # Reverse in dependency order
    op.drop_index("ix_conversations_is_pinned_created_at", table_name="conversations")
    op.drop_column("conversations", "is_archived")
    op.drop_column("conversations", "is_pinned")
    op.drop_index("ix_conversations_folder_id", table_name="conversations")
    op.drop_column("conversations", "folder_id")

    op.drop_index("ix_conversation_tag_assoc_tag", table_name="conversation_tag_associations")
    op.drop_index("ix_conversation_tag_assoc_conversation", table_name="conversation_tag_associations")
    op.drop_table("conversation_tag_associations")

    op.drop_index("ix_conversation_tags_user_id", table_name="conversation_tags")
    op.drop_table("conversation_tags")

    op.drop_index("ix_conversation_folders_user_position", table_name="conversation_folders")
    op.drop_index("ix_conversation_folders_user_id", table_name="conversation_folders")
    op.drop_table("conversation_folders")

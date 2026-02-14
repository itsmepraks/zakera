"""Initial schema for conversation persistence

Revision ID: 001
Revises: 
Create Date: 2026-02-14 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create user_preferences table
    op.create_table('user_preferences',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('theme', sa.String(length=20), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('model_preference', sa.String(length=50), nullable=True),
        sa.Column('temperature', sa.Integer(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('preferences_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('session_token', sa.String(length=255), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('device_info', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_session_expires', 'user_sessions', ['expires_at'], unique=False)
    op.create_index('idx_session_user_active', 'user_sessions', ['user_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_user_sessions_session_token'), 'user_sessions', ['session_token'], unique=True)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)

    # Create conversations table
    op.create_table('conversations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('model_name', sa.String(length=50), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True),
        sa.Column('is_pinned', sa.Boolean(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_last_message', 'conversations', ['user_id', 'last_message_at'], unique=False)
    op.create_index('idx_user_archived', 'conversations', ['user_id', 'is_archived'], unique=False)
    op.create_index('idx_user_deleted', 'conversations', ['user_id', 'is_deleted'], unique=False)
    op.create_index('idx_user_pinned', 'conversations', ['user_id', 'is_pinned'], unique=False)
    op.create_index('idx_user_updated', 'conversations', ['user_id', 'updated_at'], unique=False)
    op.create_index(op.f('ix_conversations_is_archived'), 'conversations', ['is_archived'], unique=False)
    op.create_index(op.f('ix_conversations_is_deleted'), 'conversations', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_conversations_is_pinned'), 'conversations', ['is_pinned'], unique=False)
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)

    # Create messages table
    op.create_table('messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('model_name', sa.String(length=50), nullable=True),
        sa.Column('finish_reason', sa.String(length=50), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('parent_message_id', sa.String(length=36), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['parent_message_id'], ['messages.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_conversation_created', 'messages', ['conversation_id', 'created_at'], unique=False)
    op.create_index('idx_conversation_role', 'messages', ['conversation_id', 'role'], unique=False)
    op.create_index('idx_parent_message', 'messages', ['parent_message_id'], unique=False)
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_messages_role'), 'messages', ['role'], unique=False)

    # Create conversation_shares table
    op.create_table('conversation_shares',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('share_token', sa.String(length=64), nullable=False),
        sa.Column('shared_by', sa.String(length=36), nullable=False),
        sa.Column('shared_with', sa.String(length=36), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('can_edit', sa.Boolean(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['shared_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['shared_with'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_conversation_share', 'conversation_shares', ['conversation_id'], unique=False)
    op.create_index('idx_expires', 'conversation_shares', ['expires_at'], unique=False)
    op.create_index('idx_shared_by', 'conversation_shares', ['shared_by'], unique=False)
    op.create_index(op.f('ix_conversation_shares_share_token'), 'conversation_shares', ['share_token'], unique=True)

    # Create conversation_exports table
    op.create_table('conversation_exports',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('export_format', sa.String(length=20), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_export_status', 'conversation_exports', ['status'], unique=False)
    op.create_index('idx_user_exports', 'conversation_exports', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_conversation_exports_conversation_id'), 'conversation_exports', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_exports_user_id'), 'conversation_exports', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_conversation_exports_user_id'), table_name='conversation_exports')
    op.drop_index(op.f('ix_conversation_exports_conversation_id'), table_name='conversation_exports')
    op.drop_index('idx_user_exports', table_name='conversation_exports')
    op.drop_index('idx_export_status', table_name='conversation_exports')
    op.drop_table('conversation_exports')
    
    op.drop_index(op.f('ix_conversation_shares_share_token'), table_name='conversation_shares')
    op.drop_index('idx_shared_by', table_name='conversation_shares')
    op.drop_index('idx_expires', table_name='conversation_shares')
    op.drop_index('idx_conversation_share', table_name='conversation_shares')
    op.drop_table('conversation_shares')
    
    op.drop_index(op.f('ix_messages_role'), table_name='messages')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_index('idx_parent_message', table_name='messages')
    op.drop_index('idx_conversation_role', table_name='messages')
    op.drop_index('idx_conversation_created', table_name='messages')
    op.drop_table('messages')
    
    op.drop_index(op.f('ix_conversations_user_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_is_pinned'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_is_deleted'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_is_archived'), table_name='conversations')
    op.drop_index('idx_user_updated', table_name='conversations')
    op.drop_index('idx_user_pinned', table_name='conversations')
    op.drop_index('idx_user_deleted', table_name='conversations')
    op.drop_index('idx_user_archived', table_name='conversations')
    op.drop_index('idx_last_message', table_name='conversations')
    op.drop_table('conversations')
    
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_session_token'), table_name='user_sessions')
    op.drop_index('idx_session_user_active', table_name='user_sessions')
    op.drop_index('idx_session_expires', table_name='user_sessions')
    op.drop_table('user_sessions')
    
    op.drop_table('user_preferences')
    
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

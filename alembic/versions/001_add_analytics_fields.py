"""Add analytics fields to conversations and messages.

Revision ID: 001_analytics
Revises: 
Create Date: 2026-02-15 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_analytics'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add analytics-related fields to support new features."""
    
    # Add fields to conversations table
    op.add_column('conversations',
        sa.Column('duration_seconds', sa.Integer(), nullable=True, comment='Total conversation duration')
    )
    op.add_column('conversations',
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0', comment='Total messages in conversation')
    )
    op.add_column('conversations',
        sa.Column('last_message_at', sa.DateTime(), nullable=True, comment='Timestamp of last message')
    )
    op.add_column('conversations',
        sa.Column('success_status', sa.String(20), nullable=True, comment='Conversation completion status')
    )
    op.add_column('conversations',
        sa.Column('user_feedback', sa.String(20), nullable=True, comment='User feedback (positive/negative)')
    )
    
    # Add fields to messages table
    op.add_column('messages',
        sa.Column('response_time_ms', sa.Integer(), nullable=True, comment='Model response time in milliseconds')
    )
    op.add_column('messages',
        sa.Column('prompt_tokens', sa.Integer(), nullable=True, comment='Number of prompt tokens used')
    )
    op.add_column('messages',
        sa.Column('completion_tokens', sa.Integer(), nullable=True, comment='Number of completion tokens used')
    )
    op.add_column('messages',
        sa.Column('model_provider', sa.String(50), nullable=True, comment='Model provider (openai, anthropic, ollama)')
    )
    op.add_column('messages',
        sa.Column('user_feedback', sa.String(20), nullable=True, comment='User feedback on message quality')
    )
    op.add_column('messages',
        sa.Column('regenerated_count', sa.Integer(), nullable=False, server_default='0', comment='Times message was regenerated')
    )
    
    # Create indexes for analytics queries
    op.create_index(
        'idx_conversations_created_at',
        'conversations',
        ['created_at'],
        comment='Index for date-range queries'
    )
    op.create_index(
        'idx_conversations_user_created',
        'conversations',
        ['user_id', 'created_at'],
        comment='Index for user analytics'
    )
    op.create_index(
        'idx_messages_created_at',
        'messages',
        ['created_at'],
        comment='Index for date-range queries'
    )
    op.create_index(
        'idx_messages_model',
        'messages',
        ['model'],
        comment='Index for model analytics'
    )
    op.create_index(
        'idx_messages_conversation_created',
        'messages',
        ['conversation_id', 'created_at'],
        comment='Index for conversation message queries'
    )


def downgrade() -> None:
    """Revert analytics-related changes."""
    
    # Drop indexes
    op.drop_index('idx_messages_conversation_created', table_name='messages')
    op.drop_index('idx_messages_model', table_name='messages')
    op.drop_index('idx_messages_created_at', table_name='messages')
    op.drop_index('idx_conversations_user_created', table_name='conversations')
    op.drop_index('idx_conversations_created_at', table_name='conversations')
    
    # Drop columns from messages
    op.drop_column('messages', 'regenerated_count')
    op.drop_column('messages', 'user_feedback')
    op.drop_column('messages', 'model_provider')
    op.drop_column('messages', 'completion_tokens')
    op.drop_column('messages', 'prompt_tokens')
    op.drop_column('messages', 'response_time_ms')
    
    # Drop columns from conversations
    op.drop_column('conversations', 'user_feedback')
    op.drop_column('conversations', 'success_status')
    op.drop_column('conversations', 'last_message_at')
    op.drop_column('conversations', 'message_count')
    op.drop_column('conversations', 'duration_seconds')

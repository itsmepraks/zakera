"""Add conversation templates tables

Revision ID: 001_conversation_templates
Revises: 
Create Date: 2026-03-08

This migration creates the conversation_templates and template_usage_logs tables
for managing predefined conversation starters and templates.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '001_conversation_templates'
down_revision = None  # Update this to the previous migration ID
branch_labels = None
depends_on = None


def upgrade():
    """Create conversation templates tables."""
    
    # Create conversation_templates table
    op.create_table(
        'conversation_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, comment='Template category'),
        sa.Column('difficulty', sa.String(length=20), nullable=True, comment='Difficulty level'),
        sa.Column('system_prompt', sa.Text(), nullable=False, comment='System prompt for AI behavior'),
        sa.Column('starter_message', sa.Text(), nullable=True, comment='Optional conversation starter'),
        sa.Column('suggested_questions', sa.JSON(), nullable=True, comment='List of suggested questions/prompts'),
        sa.Column('tags', sa.JSON(), nullable=True, comment='Tags for searching and filtering'),
        sa.Column('model_recommendations', sa.JSON(), nullable=True, comment='Recommended model providers'),
        sa.Column('is_public', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('usage_count', sa.Integer(), nullable=True, server_default='0', comment='Number of times used'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='User who created the template'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for conversation_templates
    op.create_index('idx_template_category_active', 'conversation_templates', ['category', 'is_active'])
    op.create_index('idx_template_created_at', 'conversation_templates', ['created_at'])
    op.create_index('idx_template_public_active', 'conversation_templates', ['is_public', 'is_active'])
    op.create_index('idx_template_usage_count', 'conversation_templates', ['usage_count'])
    op.create_index(op.f('ix_conversation_templates_category'), 'conversation_templates', ['category'])
    op.create_index(op.f('ix_conversation_templates_id'), 'conversation_templates', ['id'])
    op.create_index(op.f('ix_conversation_templates_is_active'), 'conversation_templates', ['is_active'])
    op.create_index(op.f('ix_conversation_templates_is_public'), 'conversation_templates', ['is_public'])
    op.create_index(op.f('ix_conversation_templates_title'), 'conversation_templates', ['title'])
    
    # Create template_usage_logs table
    op.create_table(
        'template_usage_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('conversation_id', sa.Integer(), nullable=True),
        sa.Column('model_used', sa.String(length=100), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['conversation_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for template_usage_logs
    op.create_index('idx_usage_template_date', 'template_usage_logs', ['template_id', 'used_at'])
    op.create_index('idx_usage_user_date', 'template_usage_logs', ['user_id', 'used_at'])
    op.create_index(op.f('ix_template_usage_logs_id'), 'template_usage_logs', ['id'])
    op.create_index(op.f('ix_template_usage_logs_template_id'), 'template_usage_logs', ['template_id'])
    op.create_index(op.f('ix_template_usage_logs_user_id'), 'template_usage_logs', ['user_id'])


def downgrade():
    """Drop conversation templates tables."""
    
    # Drop template_usage_logs table and indexes
    op.drop_index(op.f('ix_template_usage_logs_user_id'), table_name='template_usage_logs')
    op.drop_index(op.f('ix_template_usage_logs_template_id'), table_name='template_usage_logs')
    op.drop_index(op.f('ix_template_usage_logs_id'), table_name='template_usage_logs')
    op.drop_index('idx_usage_user_date', table_name='template_usage_logs')
    op.drop_index('idx_usage_template_date', table_name='template_usage_logs')
    op.drop_table('template_usage_logs')
    
    # Drop conversation_templates table and indexes
    op.drop_index(op.f('ix_conversation_templates_title'), table_name='conversation_templates')
    op.drop_index(op.f('ix_conversation_templates_is_public'), table_name='conversation_templates')
    op.drop_index(op.f('ix_conversation_templates_is_active'), table_name='conversation_templates')
    op.drop_index(op.f('ix_conversation_templates_id'), table_name='conversation_templates')
    op.drop_index(op.f('ix_conversation_templates_category'), table_name='conversation_templates')
    op.drop_index('idx_template_usage_count', table_name='conversation_templates')
    op.drop_index('idx_template_public_active', table_name='conversation_templates')
    op.drop_index('idx_template_created_at', table_name='conversation_templates')
    op.drop_index('idx_template_category_active', table_name='conversation_templates')
    op.drop_table('conversation_templates')

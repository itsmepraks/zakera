"""Add security tables and enhanced authentication

Revision ID: 002_security_enhancement
Revises: 001_initial
Create Date: 2026-02-16 03:20:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002_security_enhancement'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    """Add security tables and columns"""
    
    # ========================================================================
    # Update users table with security columns
    # ========================================================================
    op.add_column('users', sa.Column('role', sa.String(20), server_default='user'))
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), server_default='false'))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), server_default='false'))
    op.add_column('users', sa.Column('phone_verified', sa.Boolean(), server_default='false'))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_password_change', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('password_reset_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(), nullable=True))
    
    # ========================================================================
    # Create api_keys table
    # ========================================================================
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('key_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(10), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('created_from_ip', sa.String(45), nullable=True),
        sa.Column('rate_limit_per_minute', sa.Integer(), server_default='60'),
        sa.Column('rate_limit_per_hour', sa.Integer(), server_default='1000'),
    )
    op.create_index('idx_api_key_user', 'api_keys', ['user_id'])
    op.create_index('idx_api_key_hash', 'api_keys', ['key_hash'])
    
    # ========================================================================
    # Create sessions table
    # ========================================================================
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_token', sa.String(256), nullable=False, unique=True),
        sa.Column('refresh_token_hash', sa.String(64), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('device_fingerprint', sa.String(64), nullable=True),
        sa.Column('country', sa.String(2), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_activity', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_reason', sa.String(255), nullable=True),
    )
    op.create_index('idx_session_user', 'sessions', ['user_id'])
    op.create_index('idx_session_token', 'sessions', ['session_token'])
    op.create_index('idx_session_active', 'sessions', ['is_active', 'expires_at'])
    
    # ========================================================================
    # Create login_attempts table
    # ========================================================================
    op.create_table(
        'login_attempts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('attempted_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_login_username', 'login_attempts', ['username', 'attempted_at'])
    op.create_index('idx_login_ip', 'login_attempts', ['ip_address', 'attempted_at'])
    op.create_index('idx_login_user', 'login_attempts', ['user_id', 'attempted_at'])
    
    # ========================================================================
    # Create audit_logs table
    # ========================================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('changes', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('severity', sa.String(20), server_default='info'),
    )
    op.create_index('idx_audit_user', 'audit_logs', ['user_id', 'created_at'])
    op.create_index('idx_audit_action', 'audit_logs', ['action', 'created_at'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    
    # ========================================================================
    # Create oauth2_accounts table
    # ========================================================================
    op.create_table(
        'oauth2_accounts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('provider_username', sa.String(255), nullable=True),
        sa.Column('provider_email', sa.String(255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('profile_data', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_oauth_user', 'oauth2_accounts', ['user_id'])
    op.create_index('idx_oauth_provider', 'oauth2_accounts', ['provider', 'provider_user_id'])
    
    # ========================================================================
    # Create user_mfa table
    # ========================================================================
    op.create_table(
        'user_mfa',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('is_enabled', sa.Boolean(), server_default='false'),
        sa.Column('secret', sa.String(255), nullable=False),
        sa.Column('backup_codes', sa.JSON(), nullable=True),
        sa.Column('enabled_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('recovery_email', sa.String(255), nullable=True),
        sa.Column('recovery_phone', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_mfa_user', 'user_mfa', ['user_id'])
    
    # ========================================================================
    # Create password_history table
    # ========================================================================
    op.create_table(
        'password_history',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_password_history_user', 'password_history', ['user_id', 'created_at'])
    
    # ========================================================================
    # Create account_lockouts table
    # ========================================================================
    op.create_table(
        'account_lockouts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reason', sa.String(255), nullable=False),
        sa.Column('locked_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('unlocked_at', sa.DateTime(), nullable=True),
        sa.Column('auto_unlock_at', sa.DateTime(), nullable=True),
        sa.Column('failed_attempts', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
    )
    op.create_index('idx_lockout_user', 'account_lockouts', ['user_id', 'is_active'])


def downgrade():
    \"\"\"Remove security tables and columns\"\"\"
    
    # Drop tables
    op.drop_table('account_lockouts')
    op.drop_table('password_history')
    op.drop_table('user_mfa')
    op.drop_table('oauth2_accounts')
    op.drop_table('audit_logs')
    op.drop_table('login_attempts')
    op.drop_table('sessions')
    op.drop_table('api_keys')
    
    # Remove columns from users table
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'last_password_change')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'phone_verified')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'role')

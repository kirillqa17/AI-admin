"""Initial schema - Multi-tenant AI-Admin

Revision ID: 0001
Revises:
Create Date: 2026-01-10

Creates the base multi-tenant schema for AI-Admin SAAS platform.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Companies table
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('phone', sa.String(50)),
        sa.Column('subscription_plan', sa.String(50), default='free'),
        sa.Column('subscription_status', sa.String(50), default='active'),
        sa.Column('subscription_expires_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('billing_email', sa.String(255)),
    )

    # Company CRM Settings table
    op.create_table(
        'company_crm_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('companies.id', ondelete='CASCADE'),
                  nullable=False, unique=True),
        sa.Column('crm_type', sa.String(50), nullable=False),
        sa.Column('api_key_encrypted', sa.Text, nullable=False),
        sa.Column('base_url', sa.String(500)),
        sa.Column('company_id_in_crm', sa.String(255)),
        sa.Column('additional_settings', postgresql.JSONB, default={}),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_sync_at', sa.DateTime),
        sa.Column('last_sync_status', sa.String(50)),
        sa.Column('last_sync_error', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Company Agent Settings table
    op.create_table(
        'company_agent_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('companies.id', ondelete='CASCADE'),
                  nullable=False, unique=True),
        sa.Column('company_description', sa.Text),
        sa.Column('business_type', sa.String(100)),
        sa.Column('target_audience', sa.Text),
        sa.Column('working_hours', sa.String(500)),
        sa.Column('address', sa.Text),
        sa.Column('phone_display', sa.String(50)),
        sa.Column('services_catalog', postgresql.JSONB, default=[]),
        sa.Column('products_catalog', postgresql.JSONB, default=[]),
        sa.Column('business_highlights', sa.Text),
        sa.Column('greeting_message', sa.Text),
        sa.Column('farewell_message', sa.Text),
        sa.Column('custom_instructions', sa.Text),
        sa.Column('temperature', sa.DECIMAL(3, 2), default=0.7),
        sa.Column('max_tokens', sa.Integer, default=8192),
        sa.Column('model_name', sa.String(100), default='gemini-2.0-flash-exp'),
        sa.Column('custom_prompts', postgresql.JSONB, default={}),
        sa.Column('features', postgresql.JSONB, default={"auto_booking": True}),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Company Channels table
    op.create_table(
        'company_channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('companies.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('channel_type', sa.String(50), nullable=False),
        sa.Column('channel_name', sa.String(255)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('config', postgresql.JSONB, default={}),
        sa.Column('webhook_token', sa.String(255), unique=True),
        sa.Column('webhook_url', sa.String(500)),
        sa.Column('messages_received', sa.Integer, default=0),
        sa.Column('messages_sent', sa.Integer, default=0),
        sa.Column('last_activity_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('companies.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('state', sa.String(50), default='INITIATED'),
        sa.Column('context', postgresql.JSONB, default={}),
        sa.Column('crm_client_id', sa.String(255)),
        sa.Column('crm_appointment_id', sa.String(255)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_activity_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime),
    )

    # Messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('sessions.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('companies.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('message_type', sa.String(50), default='text'),
        sa.Column('text', sa.Text),
        sa.Column('audio_url', sa.String(500)),
        sa.Column('image_url', sa.String(500)),
        sa.Column('file_url', sa.String(500)),
        sa.Column('is_from_bot', sa.Boolean, default=False),
        sa.Column('from_user_id', sa.String(255)),
        sa.Column('from_user_name', sa.String(255)),
        sa.Column('message_metadata', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index('idx_sessions_company_user', 'sessions', ['company_id', 'user_id'])
    op.create_index('idx_messages_session', 'messages', ['session_id'])
    op.create_index('idx_channels_webhook_token', 'company_channels', ['webhook_token'])


def downgrade() -> None:
    op.drop_index('idx_channels_webhook_token')
    op.drop_index('idx_messages_session')
    op.drop_index('idx_sessions_company_user')

    op.drop_table('messages')
    op.drop_table('sessions')
    op.drop_table('company_channels')
    op.drop_table('company_agent_settings')
    op.drop_table('company_crm_settings')
    op.drop_table('companies')

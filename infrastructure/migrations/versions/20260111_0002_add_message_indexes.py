"""Add indexes for message history queries

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-11

Adds performance indexes for:
- Fast message queries by company_id
- Fast queries by created_at for analytics
- Composite indexes for common query patterns
- Partial indexes for active data
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========================================
    # MESSAGES INDEXES
    # ========================================

    # Индекс по company_id для быстрого получения сообщений компании
    op.create_index(
        'idx_messages_company_id',
        'messages',
        ['company_id'],
        postgresql_concurrently=False  # True for production без downtime
    )

    # Индекс по created_at для аналитики и data retention
    op.create_index(
        'idx_messages_created_at',
        'messages',
        ['created_at'],
        postgresql_concurrently=False
    )

    # Композитный индекс для частого паттерна: сообщения компании за период
    op.create_index(
        'idx_messages_company_created',
        'messages',
        ['company_id', 'created_at'],
        postgresql_concurrently=False
    )

    # Композитный индекс: сессия + время (для истории диалога)
    op.create_index(
        'idx_messages_session_created',
        'messages',
        ['session_id', 'created_at'],
        postgresql_concurrently=False
    )

    # Индекс по is_from_bot для фильтрации
    op.create_index(
        'idx_messages_is_from_bot',
        'messages',
        ['is_from_bot'],
        postgresql_concurrently=False
    )

    # ========================================
    # SESSIONS INDEXES
    # ========================================

    # Индекс по company_id для быстрого получения сессий компании
    op.create_index(
        'idx_sessions_company_id',
        'sessions',
        ['company_id'],
        postgresql_concurrently=False
    )

    # Индекс по last_activity_at для data retention
    op.create_index(
        'idx_sessions_last_activity',
        'sessions',
        ['last_activity_at'],
        postgresql_concurrently=False
    )

    # Индекс по state для аналитики
    op.create_index(
        'idx_sessions_state',
        'sessions',
        ['state'],
        postgresql_concurrently=False
    )

    # Композитный индекс: компания + состояние (для подсчета конверсий)
    op.create_index(
        'idx_sessions_company_state',
        'sessions',
        ['company_id', 'state'],
        postgresql_concurrently=False
    )

    # Композитный индекс: компания + канал (для аналитики по каналам)
    op.create_index(
        'idx_sessions_company_channel',
        'sessions',
        ['company_id', 'channel'],
        postgresql_concurrently=False
    )

    # Индекс для поиска сессий с записями (конверсии)
    op.create_index(
        'idx_sessions_with_appointment',
        'sessions',
        ['company_id', 'crm_appointment_id'],
        postgresql_where="crm_appointment_id IS NOT NULL",
        postgresql_concurrently=False
    )


def downgrade() -> None:
    # Messages indexes
    op.drop_index('idx_messages_company_id')
    op.drop_index('idx_messages_created_at')
    op.drop_index('idx_messages_company_created')
    op.drop_index('idx_messages_session_created')
    op.drop_index('idx_messages_is_from_bot')

    # Sessions indexes
    op.drop_index('idx_sessions_company_id')
    op.drop_index('idx_sessions_last_activity')
    op.drop_index('idx_sessions_state')
    op.drop_index('idx_sessions_company_state')
    op.drop_index('idx_sessions_company_channel')
    op.drop_index('idx_sessions_with_appointment')

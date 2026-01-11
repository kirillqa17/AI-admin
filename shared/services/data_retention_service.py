"""
Data Retention Service - управление политикой хранения данных

Обеспечивает:
- Автоматическую очистку старых данных
- Настраиваемые сроки хранения
- GDPR compliance (право на удаление)
- Логирование операций
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .message_repository import MessageRepository
from .session_repository import SessionRepository


logger = structlog.get_logger(__name__)


@dataclass
class RetentionPolicy:
    """Политика хранения данных"""

    # Сроки хранения в днях
    messages_retention_days: int = 365  # 1 год по умолчанию
    sessions_retention_days: int = 365  # 1 год по умолчанию

    # Минимальные сроки (для защиты от случайного удаления)
    min_retention_days: int = 30  # Минимум 30 дней

    # Batch size для удаления
    batch_size: int = 1000

    def validate(self) -> bool:
        """Проверить валидность политики"""
        return (
            self.messages_retention_days >= self.min_retention_days and
            self.sessions_retention_days >= self.min_retention_days
        )


class DataRetentionService:
    """
    Сервис для управления политикой хранения данных

    Используется для:
    - Автоматической очистки старых сообщений и сессий
    - GDPR compliance (удаление данных пользователя/компании)
    - Аналитики по объему данных
    """

    # Политики по умолчанию для разных планов подписки
    DEFAULT_POLICIES = {
        "free": RetentionPolicy(
            messages_retention_days=30,
            sessions_retention_days=30,
        ),
        "starter": RetentionPolicy(
            messages_retention_days=90,
            sessions_retention_days=90,
        ),
        "pro": RetentionPolicy(
            messages_retention_days=365,
            sessions_retention_days=365,
        ),
        "enterprise": RetentionPolicy(
            messages_retention_days=730,  # 2 года
            sessions_retention_days=730,
        ),
    }

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: AsyncSession from Database context manager
        """
        self.session = session
        self.message_repo = MessageRepository(session)
        self.session_repo = SessionRepository(session)

    def get_policy_for_plan(self, subscription_plan: str) -> RetentionPolicy:
        """
        Получить политику хранения для плана подписки

        Args:
            subscription_plan: Название плана (free, starter, pro, enterprise)

        Returns:
            RetentionPolicy
        """
        return self.DEFAULT_POLICIES.get(
            subscription_plan,
            self.DEFAULT_POLICIES["free"]
        )

    async def cleanup_company_data(
        self,
        company_id: str,
        policy: Optional[RetentionPolicy] = None,
    ) -> Dict[str, int]:
        """
        Очистить старые данные компании согласно политике

        Args:
            company_id: ID компании
            policy: Политика хранения (если None - используется default)

        Returns:
            Статистика удаленных записей
        """
        if policy is None:
            policy = RetentionPolicy()

        if not policy.validate():
            raise ValueError(
                f"Invalid retention policy: min {policy.min_retention_days} days required"
            )

        logger.info(
            "starting_data_cleanup",
            company_id=company_id,
            messages_retention=policy.messages_retention_days,
            sessions_retention=policy.sessions_retention_days
        )

        # Сначала удаляем старые сообщения (они ссылаются на сессии)
        deleted_messages = await self.message_repo.delete_old_messages(
            company_id=company_id,
            retention_days=policy.messages_retention_days,
        )

        # Затем удаляем старые сессии
        deleted_sessions = await self.session_repo.delete_old_sessions(
            company_id=company_id,
            retention_days=policy.sessions_retention_days,
        )

        result = {
            "deleted_messages": deleted_messages,
            "deleted_sessions": deleted_sessions,
        }

        logger.info(
            "data_cleanup_completed",
            company_id=company_id,
            **result
        )

        return result

    async def delete_all_company_data(self, company_id: str) -> Dict[str, int]:
        """
        Удалить ВСЕ данные компании (GDPR: право на забвение)

        ВНИМАНИЕ: Это необратимая операция!

        Args:
            company_id: ID компании

        Returns:
            Статистика удаленных записей
        """
        logger.warning(
            "deleting_all_company_data",
            company_id=company_id,
            reason="GDPR compliance or company deletion"
        )

        # Удаляем сообщения
        deleted_messages = await self.message_repo.delete_all_company_messages(
            company_id=company_id
        )

        # Удаляем сессии
        deleted_sessions = await self.session_repo.delete_all_company_sessions(
            company_id=company_id
        )

        result = {
            "deleted_messages": deleted_messages,
            "deleted_sessions": deleted_sessions,
        }

        logger.warning(
            "all_company_data_deleted",
            company_id=company_id,
            **result
        )

        return result

    async def get_data_statistics(self, company_id: str) -> Dict[str, Any]:
        """
        Получить статистику по данным компании

        Args:
            company_id: ID компании

        Returns:
            Статистика по сообщениям и сессиям
        """
        now = datetime.now(timezone.utc)
        last_30_days = now - timedelta(days=30)
        last_90_days = now - timedelta(days=90)

        # Общее количество
        total_messages = await self.message_repo.count_messages(company_id)
        total_sessions = await self.session_repo.count_sessions(company_id)

        # За последние 30 дней
        messages_30d = await self.message_repo.count_messages(
            company_id, start_date=last_30_days
        )
        sessions_30d = await self.session_repo.count_sessions(
            company_id, start_date=last_30_days
        )

        # Сообщения по каналам
        messages_by_channel = await self.message_repo.count_by_channel(company_id)
        sessions_by_channel = await self.session_repo.count_by_channel(company_id)

        # Сессии по состояниям
        sessions_by_state = await self.session_repo.count_by_state(company_id)

        # Конверсия
        conversion_rate = await self.session_repo.get_conversion_rate(company_id)

        return {
            "totals": {
                "messages": total_messages,
                "sessions": total_sessions,
            },
            "last_30_days": {
                "messages": messages_30d,
                "sessions": sessions_30d,
            },
            "by_channel": {
                "messages": messages_by_channel,
                "sessions": sessions_by_channel,
            },
            "sessions_by_state": sessions_by_state,
            "conversion_rate_30d": conversion_rate,
            "generated_at": now.isoformat(),
        }

    async def estimate_cleanup(
        self,
        company_id: str,
        policy: RetentionPolicy,
    ) -> Dict[str, int]:
        """
        Оценить количество данных для удаления

        Args:
            company_id: ID компании
            policy: Политика хранения

        Returns:
            Оценка количества записей к удалению
        """
        messages_cutoff = datetime.now(timezone.utc) - timedelta(
            days=policy.messages_retention_days
        )
        sessions_cutoff = datetime.now(timezone.utc) - timedelta(
            days=policy.sessions_retention_days
        )

        messages_to_delete = await self.message_repo.count_messages(
            company_id=company_id,
            end_date=messages_cutoff,
        )

        sessions_to_delete = await self.session_repo.count_sessions(
            company_id=company_id,
            end_date=sessions_cutoff,
        )

        return {
            "messages_to_delete": messages_to_delete,
            "sessions_to_delete": sessions_to_delete,
            "policy": {
                "messages_retention_days": policy.messages_retention_days,
                "sessions_retention_days": policy.sessions_retention_days,
            }
        }

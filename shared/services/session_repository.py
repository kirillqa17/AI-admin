"""
Session Repository - работа с сессиями в PostgreSQL

Обеспечивает:
- Персистентное хранение сессий для синхронизации с Redis
- Аналитику по сессиям
- Data retention (удаление старых сессий)
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from sqlalchemy import select, delete, update, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from ..database.models import Session as SessionModel, Message as MessageModel


logger = structlog.get_logger(__name__)


class SessionRepository:
    """
    Repository для работы с сессиями в PostgreSQL

    Используется для:
    - Синхронизации сессий из Redis в PostgreSQL
    - Аналитики по сессиям
    - Data retention
    """

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: AsyncSession from Database context manager
        """
        self.session = session

    # ========================================
    # CREATE / UPDATE
    # ========================================

    async def upsert_session(
        self,
        session_id: str,
        company_id: str,
        user_id: str,
        channel: str,
        state: str = "INITIATED",
        context: Optional[Dict[str, Any]] = None,
        crm_client_id: Optional[str] = None,
        crm_appointment_id: Optional[str] = None,
    ) -> SessionModel:
        """
        Создать или обновить сессию

        Args:
            session_id: ID сессии
            company_id: ID компании
            user_id: ID пользователя
            channel: Канал
            state: Состояние сессии
            context: Контекст диалога
            crm_client_id: ID клиента в CRM
            crm_appointment_id: ID записи в CRM

        Returns:
            SessionModel
        """
        # Проверяем существование
        existing = await self.get_session_by_id(session_id)

        if existing:
            # Обновляем
            existing.state = state
            existing.context = context or existing.context
            existing.crm_client_id = crm_client_id or existing.crm_client_id
            existing.crm_appointment_id = crm_appointment_id or existing.crm_appointment_id
            existing.last_activity_at = datetime.now(timezone.utc)
            existing.updated_at = datetime.now(timezone.utc)

            await self.session.flush()

            logger.debug(
                "session_updated_in_postgres",
                session_id=session_id,
                state=state
            )
            return existing
        else:
            # Создаем
            new_session = SessionModel(
                id=UUID(session_id) if isinstance(session_id, str) else session_id,
                company_id=UUID(company_id) if isinstance(company_id, str) else company_id,
                user_id=user_id,
                channel=channel,
                state=state,
                context=context or {},
                crm_client_id=crm_client_id,
                crm_appointment_id=crm_appointment_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_activity_at=datetime.now(timezone.utc),
            )

            self.session.add(new_session)
            await self.session.flush()

            logger.debug(
                "session_created_in_postgres",
                session_id=session_id,
                company_id=company_id,
                channel=channel
            )
            return new_session

    async def update_session_state(
        self,
        session_id: str,
        state: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Обновить состояние сессии

        Args:
            session_id: ID сессии
            state: Новое состояние
            context: Обновленный контекст

        Returns:
            True если успешно
        """
        update_data = {
            "state": state,
            "updated_at": datetime.now(timezone.utc),
            "last_activity_at": datetime.now(timezone.utc),
        }

        if context is not None:
            update_data["context"] = context

        query = (
            update(SessionModel)
            .where(SessionModel.id == session_id)
            .values(**update_data)
        )

        result = await self.session.execute(query)
        return result.rowcount > 0

    # ========================================
    # READ
    # ========================================

    async def get_session_by_id(
        self,
        session_id: str,
        include_messages: bool = False,
    ) -> Optional[SessionModel]:
        """
        Получить сессию по ID

        Args:
            session_id: ID сессии
            include_messages: Загрузить сообщения

        Returns:
            SessionModel или None
        """
        query = select(SessionModel).where(SessionModel.id == session_id)

        if include_messages:
            query = query.options(selectinload(SessionModel.messages))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self,
        company_id: str,
        user_id: str,
        limit: int = 10,
    ) -> List[SessionModel]:
        """
        Получить сессии пользователя

        Args:
            company_id: ID компании
            user_id: ID пользователя
            limit: Максимум сессий

        Returns:
            Список сессий
        """
        query = (
            select(SessionModel)
            .where(and_(
                SessionModel.company_id == company_id,
                SessionModel.user_id == user_id
            ))
            .order_by(desc(SessionModel.last_activity_at))
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_sessions(
        self,
        company_id: str,
        since: Optional[datetime] = None,
    ) -> List[SessionModel]:
        """
        Получить активные сессии

        Args:
            company_id: ID компании
            since: Активные с указанной даты

        Returns:
            Список активных сессий
        """
        if since is None:
            # По умолчанию - последние 24 часа
            since = datetime.now(timezone.utc) - timedelta(hours=24)

        query = (
            select(SessionModel)
            .where(and_(
                SessionModel.company_id == company_id,
                SessionModel.last_activity_at >= since
            ))
            .order_by(desc(SessionModel.last_activity_at))
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_sessions_with_pagination(
        self,
        company_id: str,
        page: int = 1,
        per_page: int = 50,
        channel: Optional[str] = None,
        state: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[SessionModel], int]:
        """
        Получить сессии с пагинацией для API

        Returns:
            Tuple[список сессий, общее количество]
        """
        conditions = [SessionModel.company_id == company_id]

        if channel:
            conditions.append(SessionModel.channel == channel)
        if state:
            conditions.append(SessionModel.state == state)
        if start_date:
            conditions.append(SessionModel.created_at >= start_date)
        if end_date:
            conditions.append(SessionModel.created_at <= end_date)

        # Общее количество
        count_query = select(func.count(SessionModel.id)).where(and_(*conditions))
        total = await self.session.execute(count_query)
        total_count = total.scalar() or 0

        # Данные с пагинацией
        offset = (page - 1) * per_page
        data_query = (
            select(SessionModel)
            .where(and_(*conditions))
            .order_by(desc(SessionModel.last_activity_at))
            .offset(offset)
            .limit(per_page)
        )

        result = await self.session.execute(data_query)
        sessions = list(result.scalars().all())

        return sessions, total_count

    # ========================================
    # ANALYTICS
    # ========================================

    async def count_sessions(
        self,
        company_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Подсчитать количество сессий"""
        conditions = [SessionModel.company_id == company_id]

        if start_date:
            conditions.append(SessionModel.created_at >= start_date)
        if end_date:
            conditions.append(SessionModel.created_at <= end_date)

        query = select(func.count(SessionModel.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_by_state(
        self,
        company_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Подсчитать сессии по состояниям"""
        conditions = [SessionModel.company_id == company_id]

        if start_date:
            conditions.append(SessionModel.created_at >= start_date)
        if end_date:
            conditions.append(SessionModel.created_at <= end_date)

        query = (
            select(SessionModel.state, func.count(SessionModel.id))
            .where(and_(*conditions))
            .group_by(SessionModel.state)
        )

        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def count_by_channel(
        self,
        company_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Подсчитать сессии по каналам"""
        conditions = [SessionModel.company_id == company_id]

        if start_date:
            conditions.append(SessionModel.created_at >= start_date)
        if end_date:
            conditions.append(SessionModel.created_at <= end_date)

        query = (
            select(SessionModel.channel, func.count(SessionModel.id))
            .where(and_(*conditions))
            .group_by(SessionModel.channel)
        )

        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def get_completed_sessions_count(
        self,
        company_id: str,
        days: int = 30,
    ) -> int:
        """Количество успешно завершенных сессий (с записью)"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(func.count(SessionModel.id)).where(and_(
            SessionModel.company_id == company_id,
            SessionModel.state == "COMPLETED",
            SessionModel.crm_appointment_id.isnot(None),
            SessionModel.created_at >= start_date
        ))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_conversion_rate(
        self,
        company_id: str,
        days: int = 30,
    ) -> float:
        """
        Посчитать конверсию (% сессий с записью)

        Returns:
            Процент конверсии (0.0 - 100.0)
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        total_query = select(func.count(SessionModel.id)).where(and_(
            SessionModel.company_id == company_id,
            SessionModel.created_at >= start_date
        ))
        total_result = await self.session.execute(total_query)
        total = total_result.scalar() or 0

        if total == 0:
            return 0.0

        completed_query = select(func.count(SessionModel.id)).where(and_(
            SessionModel.company_id == company_id,
            SessionModel.state == "COMPLETED",
            SessionModel.crm_appointment_id.isnot(None),
            SessionModel.created_at >= start_date
        ))
        completed_result = await self.session.execute(completed_query)
        completed = completed_result.scalar() or 0

        return round((completed / total) * 100, 2)

    # ========================================
    # DATA RETENTION
    # ========================================

    async def delete_old_sessions(
        self,
        company_id: str,
        retention_days: int,
    ) -> int:
        """
        Удалить сессии старше указанного срока

        ВАЖНО: Сообщения удаляются каскадно (ON DELETE CASCADE)

        Args:
            company_id: ID компании
            retention_days: Хранить сессии не старше N дней

        Returns:
            Количество удаленных сессий
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        # Подсчитаем сначала
        count_query = select(func.count(SessionModel.id)).where(and_(
            SessionModel.company_id == company_id,
            SessionModel.last_activity_at < cutoff_date
        ))
        count_result = await self.session.execute(count_query)
        count = count_result.scalar() or 0

        if count > 0:
            # Удаляем (сообщения удалятся каскадно)
            delete_query = delete(SessionModel).where(and_(
                SessionModel.company_id == company_id,
                SessionModel.last_activity_at < cutoff_date
            ))
            await self.session.execute(delete_query)

            logger.info(
                "old_sessions_deleted",
                company_id=company_id,
                retention_days=retention_days,
                deleted_count=count
            )

        return count

    async def delete_all_company_sessions(self, company_id: str) -> int:
        """
        Удалить все сессии компании (для GDPR compliance)

        Args:
            company_id: ID компании

        Returns:
            Количество удаленных сессий
        """
        count_query = select(func.count(SessionModel.id)).where(
            SessionModel.company_id == company_id
        )
        count_result = await self.session.execute(count_query)
        count = count_result.scalar() or 0

        if count > 0:
            delete_query = delete(SessionModel).where(
                SessionModel.company_id == company_id
            )
            await self.session.execute(delete_query)

            logger.warning(
                "all_company_sessions_deleted",
                company_id=company_id,
                deleted_count=count
            )

        return count

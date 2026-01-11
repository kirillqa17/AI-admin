"""
Message Repository - работа с сообщениями в PostgreSQL

Обеспечивает:
- Персистентное хранение сообщений для аналитики и аудита
- Быстрый поиск по company_id, session_id, created_at
- Пагинация для API
- Data retention (удаление старых данных)
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from sqlalchemy import select, delete, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..database.models import Message as MessageModel, Session as SessionModel


logger = structlog.get_logger(__name__)


class MessageRepository:
    """
    Repository для работы с сообщениями в PostgreSQL

    Используется для:
    - Сохранения всех сообщений для аналитики
    - Получения истории диалогов
    - Аудита и отчетности
    - Data retention (очистка старых данных)
    """

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: AsyncSession from Database context manager
        """
        self.session = session

    # ========================================
    # CREATE
    # ========================================

    async def save_message(
        self,
        session_id: str,
        company_id: str,
        channel: str,
        text: Optional[str],
        is_from_bot: bool,
        from_user_id: Optional[str] = None,
        from_user_name: Optional[str] = None,
        message_type: str = "text",
        audio_url: Optional[str] = None,
        image_url: Optional[str] = None,
        file_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MessageModel:
        """
        Сохранить сообщение в PostgreSQL

        Args:
            session_id: ID сессии диалога
            company_id: ID компании (multi-tenant)
            channel: Канал (telegram, whatsapp, voice, web)
            text: Текст сообщения
            is_from_bot: True если сообщение от бота
            from_user_id: ID пользователя
            from_user_name: Имя пользователя
            message_type: Тип сообщения (text, audio, image, etc.)
            audio_url: URL аудио файла
            image_url: URL изображения
            file_url: URL файла
            metadata: Дополнительные данные

        Returns:
            Созданный объект MessageModel
        """
        message = MessageModel(
            id=uuid4(),
            session_id=UUID(session_id) if isinstance(session_id, str) else session_id,
            company_id=UUID(company_id) if isinstance(company_id, str) else company_id,
            channel=channel,
            message_type=message_type,
            text=text,
            audio_url=audio_url,
            image_url=image_url,
            file_url=file_url,
            is_from_bot=is_from_bot,
            from_user_id=from_user_id,
            from_user_name=from_user_name,
            message_metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(message)
        await self.session.flush()  # Получаем ID без commit

        logger.debug(
            "message_saved_to_postgres",
            message_id=str(message.id),
            session_id=session_id,
            company_id=company_id,
            is_from_bot=is_from_bot
        )

        return message

    async def save_user_message(
        self,
        session_id: str,
        company_id: str,
        channel: str,
        text: str,
        from_user_id: str,
        from_user_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MessageModel:
        """Shortcut для сохранения сообщения пользователя"""
        return await self.save_message(
            session_id=session_id,
            company_id=company_id,
            channel=channel,
            text=text,
            is_from_bot=False,
            from_user_id=from_user_id,
            from_user_name=from_user_name,
            metadata=metadata,
        )

    async def save_bot_message(
        self,
        session_id: str,
        company_id: str,
        channel: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MessageModel:
        """Shortcut для сохранения сообщения бота"""
        return await self.save_message(
            session_id=session_id,
            company_id=company_id,
            channel=channel,
            text=text,
            is_from_bot=True,
            from_user_id="bot",
            from_user_name="AI Assistant",
            metadata=metadata,
        )

    # ========================================
    # READ
    # ========================================

    async def get_message_by_id(self, message_id: str) -> Optional[MessageModel]:
        """Получить сообщение по ID"""
        result = await self.session.execute(
            select(MessageModel).where(MessageModel.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
        order_desc: bool = False,
    ) -> List[MessageModel]:
        """
        Получить сообщения сессии

        Args:
            session_id: ID сессии
            limit: Максимум сообщений
            offset: Смещение для пагинации
            order_desc: True для сортировки от новых к старым

        Returns:
            Список сообщений
        """
        query = (
            select(MessageModel)
            .where(MessageModel.session_id == session_id)
            .offset(offset)
            .limit(limit)
        )

        if order_desc:
            query = query.order_by(desc(MessageModel.created_at))
        else:
            query = query.order_by(MessageModel.created_at)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_company_messages(
        self,
        company_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        channel: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MessageModel]:
        """
        Получить сообщения компании с фильтрацией

        Args:
            company_id: ID компании
            start_date: Начало периода
            end_date: Конец периода
            channel: Фильтр по каналу
            limit: Максимум сообщений
            offset: Смещение для пагинации

        Returns:
            Список сообщений
        """
        conditions = [MessageModel.company_id == company_id]

        if start_date:
            conditions.append(MessageModel.created_at >= start_date)
        if end_date:
            conditions.append(MessageModel.created_at <= end_date)
        if channel:
            conditions.append(MessageModel.channel == channel)

        query = (
            select(MessageModel)
            .where(and_(*conditions))
            .order_by(desc(MessageModel.created_at))
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_messages_with_pagination(
        self,
        company_id: str,
        page: int = 1,
        per_page: int = 50,
        session_id: Optional[str] = None,
        channel: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[MessageModel], int]:
        """
        Получить сообщения с пагинацией для API

        Args:
            company_id: ID компании
            page: Номер страницы (начиная с 1)
            per_page: Сообщений на страницу
            session_id: Фильтр по сессии
            channel: Фильтр по каналу
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            Tuple[список сообщений, общее количество]
        """
        conditions = [MessageModel.company_id == company_id]

        if session_id:
            conditions.append(MessageModel.session_id == session_id)
        if channel:
            conditions.append(MessageModel.channel == channel)
        if start_date:
            conditions.append(MessageModel.created_at >= start_date)
        if end_date:
            conditions.append(MessageModel.created_at <= end_date)

        # Общее количество
        count_query = select(func.count(MessageModel.id)).where(and_(*conditions))
        total = await self.session.execute(count_query)
        total_count = total.scalar() or 0

        # Данные с пагинацией
        offset = (page - 1) * per_page
        data_query = (
            select(MessageModel)
            .where(and_(*conditions))
            .order_by(desc(MessageModel.created_at))
            .offset(offset)
            .limit(per_page)
        )

        result = await self.session.execute(data_query)
        messages = list(result.scalars().all())

        return messages, total_count

    # ========================================
    # ANALYTICS
    # ========================================

    async def count_messages(
        self,
        company_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        channel: Optional[str] = None,
    ) -> int:
        """Подсчитать количество сообщений"""
        conditions = [MessageModel.company_id == company_id]

        if start_date:
            conditions.append(MessageModel.created_at >= start_date)
        if end_date:
            conditions.append(MessageModel.created_at <= end_date)
        if channel:
            conditions.append(MessageModel.channel == channel)

        query = select(func.count(MessageModel.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_by_channel(
        self,
        company_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Подсчитать сообщения по каналам"""
        conditions = [MessageModel.company_id == company_id]

        if start_date:
            conditions.append(MessageModel.created_at >= start_date)
        if end_date:
            conditions.append(MessageModel.created_at <= end_date)

        query = (
            select(MessageModel.channel, func.count(MessageModel.id))
            .where(and_(*conditions))
            .group_by(MessageModel.channel)
        )

        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def get_daily_message_count(
        self,
        company_id: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Получить количество сообщений по дням

        Args:
            company_id: ID компании
            days: Количество дней для анализа

        Returns:
            Список {date, count}
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(
                func.date(MessageModel.created_at).label('date'),
                func.count(MessageModel.id).label('count')
            )
            .where(and_(
                MessageModel.company_id == company_id,
                MessageModel.created_at >= start_date
            ))
            .group_by(func.date(MessageModel.created_at))
            .order_by(func.date(MessageModel.created_at))
        )

        result = await self.session.execute(query)
        return [{"date": str(row.date), "count": row.count} for row in result.all()]

    # ========================================
    # DATA RETENTION
    # ========================================

    async def delete_old_messages(
        self,
        company_id: str,
        retention_days: int,
    ) -> int:
        """
        Удалить сообщения старше указанного срока

        Args:
            company_id: ID компании
            retention_days: Хранить сообщения не старше N дней

        Returns:
            Количество удаленных сообщений
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        # Подсчитаем сначала
        count_query = select(func.count(MessageModel.id)).where(and_(
            MessageModel.company_id == company_id,
            MessageModel.created_at < cutoff_date
        ))
        count_result = await self.session.execute(count_query)
        count = count_result.scalar() or 0

        if count > 0:
            # Удаляем
            delete_query = delete(MessageModel).where(and_(
                MessageModel.company_id == company_id,
                MessageModel.created_at < cutoff_date
            ))
            await self.session.execute(delete_query)

            logger.info(
                "old_messages_deleted",
                company_id=company_id,
                retention_days=retention_days,
                deleted_count=count
            )

        return count

    async def delete_all_company_messages(self, company_id: str) -> int:
        """
        Удалить все сообщения компании (для GDPR compliance)

        Args:
            company_id: ID компании

        Returns:
            Количество удаленных сообщений
        """
        count_query = select(func.count(MessageModel.id)).where(
            MessageModel.company_id == company_id
        )
        count_result = await self.session.execute(count_query)
        count = count_result.scalar() or 0

        if count > 0:
            delete_query = delete(MessageModel).where(
                MessageModel.company_id == company_id
            )
            await self.session.execute(delete_query)

            logger.warning(
                "all_company_messages_deleted",
                company_id=company_id,
                deleted_count=count
            )

        return count

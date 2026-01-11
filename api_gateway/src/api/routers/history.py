"""
History Router - API для истории сообщений и аналитики

Эндпоинты:
- GET /sessions - список сессий компании
- GET /sessions/{session_id} - детали сессии с сообщениями
- GET /messages - список сообщений с фильтрацией
- GET /analytics - аналитика по сообщениям и сессиям
- POST /cleanup - очистка старых данных
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import structlog

from shared.database.connection import Database
from shared.services.message_repository import MessageRepository
from shared.services.session_repository import SessionRepository
from shared.services.data_retention_service import DataRetentionService, RetentionPolicy
from ...config import settings
from ...core.security import verify_api_key

router = APIRouter()
logger = structlog.get_logger(__name__)

# Database connection
db = Database(settings.postgres_url)


# ========================================
# PYDANTIC MODELS
# ========================================

class MessageResponse(BaseModel):
    """Модель ответа для сообщения"""
    id: str
    session_id: str
    company_id: str
    channel: str
    message_type: str
    text: Optional[str]
    is_from_bot: bool
    from_user_id: Optional[str]
    from_user_name: Optional[str]
    created_at: datetime


class SessionResponse(BaseModel):
    """Модель ответа для сессии"""
    id: str
    company_id: str
    user_id: str
    channel: str
    state: str
    context: Dict[str, Any]
    crm_client_id: Optional[str]
    crm_appointment_id: Optional[str]
    created_at: datetime
    last_activity_at: datetime


class SessionWithMessagesResponse(SessionResponse):
    """Сессия с сообщениями"""
    messages: List[MessageResponse]


class PaginatedResponse(BaseModel):
    """Базовая модель для пагинации"""
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int


class AnalyticsResponse(BaseModel):
    """Аналитика"""
    totals: Dict[str, int]
    last_30_days: Dict[str, int]
    by_channel: Dict[str, Dict[str, int]]
    sessions_by_state: Dict[str, int]
    conversion_rate_30d: float
    generated_at: str


class CleanupRequest(BaseModel):
    """Запрос на очистку данных"""
    messages_retention_days: int = Field(default=365, ge=30, description="Хранить сообщения N дней")
    sessions_retention_days: int = Field(default=365, ge=30, description="Хранить сессии N дней")


class CleanupResponse(BaseModel):
    """Результат очистки"""
    deleted_messages: int
    deleted_sessions: int
    policy_applied: Dict[str, int]


# ========================================
# HELPER FUNCTIONS
# ========================================

def model_to_message_response(model) -> MessageResponse:
    """Конвертация SQLAlchemy модели в Pydantic"""
    return MessageResponse(
        id=str(model.id),
        session_id=str(model.session_id),
        company_id=str(model.company_id),
        channel=model.channel,
        message_type=model.message_type,
        text=model.text,
        is_from_bot=model.is_from_bot,
        from_user_id=model.from_user_id,
        from_user_name=model.from_user_name,
        created_at=model.created_at,
    )


def model_to_session_response(model) -> SessionResponse:
    """Конвертация SQLAlchemy модели в Pydantic"""
    return SessionResponse(
        id=str(model.id),
        company_id=str(model.company_id),
        user_id=model.user_id,
        channel=model.channel,
        state=model.state,
        context=model.context or {},
        crm_client_id=model.crm_client_id,
        crm_appointment_id=model.crm_appointment_id,
        created_at=model.created_at,
        last_activity_at=model.last_activity_at,
    )


# ========================================
# ENDPOINTS
# ========================================

@router.get("/sessions", response_model=PaginatedResponse)
async def list_sessions(
    company_id: str = Query(..., description="ID компании"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(50, ge=1, le=100, description="Записей на страницу"),
    channel: Optional[str] = Query(None, description="Фильтр по каналу"),
    state: Optional[str] = Query(None, description="Фильтр по состоянию"),
    start_date: Optional[datetime] = Query(None, description="Начало периода"),
    end_date: Optional[datetime] = Query(None, description="Конец периода"),
    _: str = Depends(verify_api_key),
):
    """
    Получить список сессий компании с пагинацией

    - **company_id**: ID компании (обязательно)
    - **page**: Номер страницы (начиная с 1)
    - **per_page**: Записей на страницу (1-100)
    - **channel**: Фильтр по каналу (telegram, whatsapp, voice, web)
    - **state**: Фильтр по состоянию (INITIATED, GREETING, BOOKING, COMPLETED, etc.)
    """
    async with db.session() as db_session:
        session_repo = SessionRepository(db_session)

        sessions, total = await session_repo.get_sessions_with_pagination(
            company_id=company_id,
            page=page,
            per_page=per_page,
            channel=channel,
            state=state,
            start_date=start_date,
            end_date=end_date,
        )

        items = [model_to_session_response(s) for s in sessions]
        pages = (total + per_page - 1) // per_page

        logger.info(
            "sessions_listed",
            company_id=company_id,
            total=total,
            page=page
        )

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )


@router.get("/sessions/{session_id}", response_model=SessionWithMessagesResponse)
async def get_session_with_messages(
    session_id: str,
    _: str = Depends(verify_api_key),
):
    """
    Получить детали сессии со всеми сообщениями

    - **session_id**: ID сессии
    """
    async with db.session() as db_session:
        session_repo = SessionRepository(db_session)
        message_repo = MessageRepository(db_session)

        session = await session_repo.get_session_by_id(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = await message_repo.get_session_messages(
            session_id=session_id,
            limit=1000,
            order_desc=False,
        )

        session_data = model_to_session_response(session)

        return SessionWithMessagesResponse(
            **session_data.model_dump(),
            messages=[model_to_message_response(m) for m in messages],
        )


@router.get("/messages", response_model=PaginatedResponse)
async def list_messages(
    company_id: str = Query(..., description="ID компании"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(50, ge=1, le=100, description="Записей на страницу"),
    session_id: Optional[str] = Query(None, description="Фильтр по сессии"),
    channel: Optional[str] = Query(None, description="Фильтр по каналу"),
    start_date: Optional[datetime] = Query(None, description="Начало периода"),
    end_date: Optional[datetime] = Query(None, description="Конец периода"),
    _: str = Depends(verify_api_key),
):
    """
    Получить список сообщений компании с пагинацией

    - **company_id**: ID компании (обязательно)
    - **page**: Номер страницы (начиная с 1)
    - **per_page**: Записей на страницу (1-100)
    - **session_id**: Фильтр по конкретной сессии
    - **channel**: Фильтр по каналу
    """
    async with db.session() as db_session:
        message_repo = MessageRepository(db_session)

        messages, total = await message_repo.get_messages_with_pagination(
            company_id=company_id,
            page=page,
            per_page=per_page,
            session_id=session_id,
            channel=channel,
            start_date=start_date,
            end_date=end_date,
        )

        items = [model_to_message_response(m) for m in messages]
        pages = (total + per_page - 1) // per_page

        logger.info(
            "messages_listed",
            company_id=company_id,
            total=total,
            page=page
        )

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    company_id: str = Query(..., description="ID компании"),
    _: str = Depends(verify_api_key),
):
    """
    Получить аналитику по сообщениям и сессиям компании

    Возвращает:
    - Общее количество сообщений и сессий
    - Статистику за последние 30 дней
    - Разбивку по каналам
    - Распределение по состояниям сессий
    - Конверсию (% сессий с записью)
    """
    async with db.session() as db_session:
        retention_service = DataRetentionService(db_session)

        stats = await retention_service.get_data_statistics(company_id)

        logger.info(
            "analytics_retrieved",
            company_id=company_id
        )

        return AnalyticsResponse(**stats)


@router.get("/analytics/daily")
async def get_daily_analytics(
    company_id: str = Query(..., description="ID компании"),
    days: int = Query(30, ge=1, le=365, description="Количество дней"),
    _: str = Depends(verify_api_key),
):
    """
    Получить ежедневную статистику по сообщениям

    - **days**: Количество дней для анализа (1-365)
    """
    async with db.session() as db_session:
        message_repo = MessageRepository(db_session)

        daily_stats = await message_repo.get_daily_message_count(
            company_id=company_id,
            days=days,
        )

        return {
            "company_id": company_id,
            "days": days,
            "data": daily_stats,
        }


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_old_data(
    company_id: str = Query(..., description="ID компании"),
    request: CleanupRequest = None,
    _: str = Depends(verify_api_key),
):
    """
    Очистить старые данные компании

    ВНИМАНИЕ: Эта операция необратима!

    - **messages_retention_days**: Хранить сообщения не старше N дней (минимум 30)
    - **sessions_retention_days**: Хранить сессии не старше N дней (минимум 30)
    """
    if request is None:
        request = CleanupRequest()

    policy = RetentionPolicy(
        messages_retention_days=request.messages_retention_days,
        sessions_retention_days=request.sessions_retention_days,
    )

    async with db.session() as db_session:
        retention_service = DataRetentionService(db_session)

        result = await retention_service.cleanup_company_data(
            company_id=company_id,
            policy=policy,
        )

        logger.warning(
            "data_cleanup_executed",
            company_id=company_id,
            **result
        )

        return CleanupResponse(
            deleted_messages=result["deleted_messages"],
            deleted_sessions=result["deleted_sessions"],
            policy_applied={
                "messages_retention_days": policy.messages_retention_days,
                "sessions_retention_days": policy.sessions_retention_days,
            }
        )


@router.post("/cleanup/estimate")
async def estimate_cleanup(
    company_id: str = Query(..., description="ID компании"),
    request: CleanupRequest = None,
    _: str = Depends(verify_api_key),
):
    """
    Оценить количество данных для удаления (без фактического удаления)

    Полезно для предварительной оценки перед очисткой
    """
    if request is None:
        request = CleanupRequest()

    policy = RetentionPolicy(
        messages_retention_days=request.messages_retention_days,
        sessions_retention_days=request.sessions_retention_days,
    )

    async with db.session() as db_session:
        retention_service = DataRetentionService(db_session)

        estimate = await retention_service.estimate_cleanup(
            company_id=company_id,
            policy=policy,
        )

        return estimate

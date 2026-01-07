"""
Session models для управления состоянием диалогов
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SessionState(str, Enum):
    """Состояния сессии диалога"""
    INITIATED = "initiated"  # Диалог начат
    GREETING = "greeting"  # Приветствие
    COLLECTING_INFO = "collecting_info"  # Сбор информации о клиенте
    CONSULTING = "consulting"  # Консультация
    BOOKING = "booking"  # Процесс записи
    CONFIRMING = "confirming"  # Подтверждение записи
    COMPLETED = "completed"  # Диалог завершен
    FAILED = "failed"  # Ошибка в процессе


class Session(BaseModel):
    """Модель сессии диалога с клиентом"""
    
    id: str = Field(..., description="Уникальный ID сессии")
    user_id: str = Field(..., description="ID пользователя")
    channel: str = Field(..., description="Канал коммуникации")

    # Multi-tenant
    company_id: Optional[str] = Field(None, description="ID компании (для multi-tenant)")

    # Состояние
    state: SessionState = Field(default=SessionState.INITIATED)
    
    # История сообщений (краткая, для контекста)
    message_ids: List[str] = Field(default_factory=list, description="IDs сообщений в сессии")
    
    # Контекст диалога
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Контекст: собранные данные, намерения пользователя и т.д."
    )
    
    # CRM связь
    crm_client_id: Optional[str] = Field(None, description="ID клиента в CRM")
    crm_appointment_id: Optional[str] = Field(None, description="ID записи в CRM")
    
    # Метаданные
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # TTL для Redis (в секундах) - например, 24 часа
    ttl: int = Field(default=86400, description="Time to live в секундах")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "sess_123",
                "user_id": "user_456",
                "channel": "telegram",
                "state": "collecting_info",
                "context": {
                    "name": "Иван",
                    "phone": "+79001234567",
                    "desired_service": "стрижка",
                    "desired_date": "2026-01-15"
                },
                "crm_client_id": "crm_client_789"
            }
        }

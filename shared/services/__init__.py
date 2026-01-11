"""
Shared services

Сервисы для работы с данными:
- CompanyService: работа с компаниями и их настройками
- MessageRepository: персистентное хранение сообщений
- SessionRepository: персистентное хранение сессий
- DataRetentionService: управление политикой хранения данных
"""

from .company_service import CompanyService
from .message_repository import MessageRepository
from .session_repository import SessionRepository
from .data_retention_service import DataRetentionService, RetentionPolicy

__all__ = [
    "CompanyService",
    "MessageRepository",
    "SessionRepository",
    "DataRetentionService",
    "RetentionPolicy",
]

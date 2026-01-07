"""
Request/Response models для API Gateway
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class MessageRequest(BaseModel):
    """Запрос на обработку сообщения"""
    session_id: str = Field(..., description="ID сессии диалога")
    user_id: str = Field(..., description="ID пользователя")
    channel: str = Field(..., description="Канал: telegram, whatsapp, voice, web")
    text: str = Field(..., description="Текст сообщения")
    user_name: Optional[str] = Field(None, description="Имя пользователя")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Доп. метаданные")


class MessageResponse(BaseModel):
    """Ответ на сообщение"""
    session_id: str
    message_id: str
    text: Optional[str] = None
    state: str
    context: Dict[str, Any] = Field(default_factory=dict)
    function_called: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Ответ health check"""
    status: str
    version: str
    services: Dict[str, bool]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

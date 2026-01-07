"""
Message models для межсервисного общения
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class Channel(str, Enum):
    """Каналы коммуникации"""
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    VOICE = "voice"
    WEB = "web"


class MessageType(str, Enum):
    """Типы сообщений"""
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACT = "contact"


class Message(BaseModel):
    """Универсальная модель сообщения"""
    
    id: str = Field(..., description="Уникальный ID сообщения")
    session_id: str = Field(..., description="ID сессии диалога")
    channel: Channel = Field(..., description="Канал коммуникации")
    type: MessageType = Field(default=MessageType.TEXT, description="Тип сообщения")
    
    # Содержимое
    text: Optional[str] = Field(None, description="Текст сообщения")
    audio_url: Optional[str] = Field(None, description="URL аудио файла")
    image_url: Optional[str] = Field(None, description="URL изображения")
    file_url: Optional[str] = Field(None, description="URL файла")
    
    # Метаданные
    from_user_id: str = Field(..., description="ID пользователя отправителя")
    from_user_name: Optional[str] = Field(None, description="Имя пользователя")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Дополнительные данные (channel-specific)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Флаги
    is_from_bot: bool = Field(default=False, description="Сообщение от бота")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg_123",
                "session_id": "sess_456",
                "channel": "telegram",
                "type": "text",
                "text": "Здравствуйте, хочу записаться на стрижку",
                "from_user_id": "user_789",
                "from_user_name": "Иван Иванов",
            }
        }

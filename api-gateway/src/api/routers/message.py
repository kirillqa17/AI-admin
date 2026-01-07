"""
Message Router - универсальный эндпоинт для обработки сообщений
"""

from fastapi import APIRouter, HTTPException
import uuid
import structlog
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from shared.models.message import Message, MessageType, Channel
from ...models.requests import MessageRequest, MessageResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/", response_model=MessageResponse)
async def process_message(request: MessageRequest):
    """
    Универсальный эндпоинт для обработки сообщений
    
    Принимает сообщения от любых каналов и передает в AI Agent
    """
    logger.info(
        "processing_message",
        session_id=request.session_id,
        channel=request.channel,
        user_id=request.user_id
    )
    
    try:
        # Создаем Message объект
        message = Message(
            id=str(uuid.uuid4()),
            session_id=request.session_id,
            channel=Channel(request.channel),
            type=MessageType.TEXT,
            text=request.text,
            from_user_id=request.user_id,
            from_user_name=request.user_name,
            metadata=request.metadata
        )
        
        # TODO: Передать сообщение в AI Agent через Orchestrator
        # Пока возвращаем заглушку
        
        logger.info("message_processed", message_id=message.id)
        
        return MessageResponse(
            session_id=message.session_id,
            message_id=message.id,
            text="Спасибо за ваше сообщение! Я обрабатываю ваш запрос...",
            state="PROCESSING",
            context={}
        )
        
    except Exception as e:
        logger.error("message_processing_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

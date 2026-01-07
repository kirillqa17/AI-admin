"""
Telegram Webhook Router (Multi-tenant)
"""

from fastapi import APIRouter, Request, HTTPException
import structlog
import uuid
import httpx

from shared.models.message import Message, MessageType, Channel
from shared.database.connection import Database
from shared.services.company_service import CompanyService
from ...config import settings

router = APIRouter()
logger = structlog.get_logger(__name__)

# Database connection
db = Database(settings.postgres_url)

# HTTP client for AI Agent
ai_agent_client = httpx.AsyncClient(base_url=settings.ai_agent_url, timeout=30.0)


@router.post("/webhook/{webhook_token}")
async def telegram_webhook(webhook_token: str, request: Request):
    """
    Webhook для Telegram Bot API (Multi-tenant)

    Принимает обновления от Telegram
    URL содержит уникальный токен компании для определения company_id
    """
    try:
        update = await request.json()

        logger.info(
            "telegram_update_received",
            update_id=update.get("update_id"),
            webhook_token=webhook_token
        )

        # 1. MULTI-TENANT: Определяем company_id по webhook токену
        async with db.session() as db_session:
            company_service = CompanyService(db_session)
            channel = await company_service.get_channel_by_token(webhook_token)

            if not channel:
                logger.warning("channel_not_found", webhook_token=webhook_token)
                raise HTTPException(status_code=404, detail="Channel not found")

            if not channel.is_active:
                logger.warning("channel_inactive", webhook_token=webhook_token)
                raise HTTPException(status_code=403, detail="Channel is inactive")

            company_id = str(channel.company_id)

            # 2. Извлекаем сообщение из Telegram update
            if "message" not in update:
                logger.debug("no_message_in_update", update_id=update.get("update_id"))
                return {"ok": True}

            tg_message = update["message"]
            tg_user = tg_message.get("from", {})
            tg_user_id = str(tg_user.get("id"))

            # 3. MULTI-TENANT: Создаем Message с company_id
            message = Message(
                id=str(uuid.uuid4()),
                session_id=f"tg_{tg_user_id}",
                channel=Channel.TELEGRAM,
                type=MessageType.TEXT,
                text=tg_message.get("text", ""),
                from_user_id=tg_user_id,
                from_user_name=tg_user.get("first_name"),
                company_id=company_id,  # MULTI-TENANT!
                metadata={
                    "telegram_chat_id": tg_message.get("chat", {}).get("id"),
                    "telegram_message_id": tg_message.get("message_id")
                }
            )

            logger.info(
                "telegram_message_created",
                message_id=message.id,
                company_id=company_id,
                user_id=tg_user_id
            )

            # 4. Передать в AI Agent
            try:
                response = await ai_agent_client.post(
                    "/process",
                    json=message.model_dump(mode='json')
                )
                response.raise_for_status()
                result = response.json()

                logger.info(
                    "ai_agent_response_received",
                    message_id=message.id,
                    has_function_call=result.get("function_called", False)
                )

                # TODO: Отправить ответ пользователю в Telegram

            except httpx.HTTPError as e:
                logger.error(
                    "ai_agent_request_error",
                    message_id=message.id,
                    error=str(e)
                )
                # Не падаем, просто логируем ошибку

            return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("telegram_webhook_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook")
async def telegram_webhook_info():
    """Информация о webhook"""
    return {
        "status": "active",
        "description": "Telegram webhook endpoint"
    }

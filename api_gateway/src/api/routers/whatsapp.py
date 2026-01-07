"""
WhatsApp Webhook Router (Multi-tenant)
"""

from fastapi import APIRouter, Request, HTTPException, Query
import structlog
import uuid

from shared.models.message import Message, MessageType, Channel
from shared.database.connection import Database
from shared.services.company_service import CompanyService
from ...config import settings

router = APIRouter()
logger = structlog.get_logger(__name__)

# Database connection
db = Database(settings.postgres_url)


@router.get("/webhook/{webhook_token}")
async def whatsapp_webhook_verify(
    webhook_token: str,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Верификация webhook для WhatsApp Business API (Multi-tenant)

    Facebook/WhatsApp требует GET запрос для верификации
    """
    logger.info("whatsapp_verification_request", mode=hub_mode, webhook_token=webhook_token)

    # MULTI-TENANT: Проверяем что канал существует
    async with db.session() as db_session:
        company_service = CompanyService(db_session)
        channel = await company_service.get_channel_by_token(webhook_token)

        if not channel:
            logger.warning("channel_not_found_verification", webhook_token=webhook_token)
            raise HTTPException(status_code=404, detail="Channel not found")

    # TODO: проверить hub_verify_token против channel.config
    if hub_mode == "subscribe":
        return int(hub_challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/{webhook_token}")
async def whatsapp_webhook(webhook_token: str, request: Request):
    """
    Webhook для WhatsApp Business API (Multi-tenant)

    Принимает сообщения от WhatsApp
    URL содержит уникальный токен компании для определения company_id
    """
    try:
        payload = await request.json()

        logger.info("whatsapp_payload_received", webhook_token=webhook_token)

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

            # 2. Извлекаем сообщение из WhatsApp payload
            # WhatsApp API структура: {"entry": [{"changes": [{"value": {"messages": [...]}}]}]}
            if "entry" not in payload:
                logger.debug("no_entry_in_payload")
                return {"status": "success"}

            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])

                    for wa_message in messages:
                        wa_from = wa_message.get("from")
                        wa_text = wa_message.get("text", {}).get("body", "")
                        wa_type = wa_message.get("type", "text")

                        # 3. MULTI-TENANT: Создаем Message с company_id
                        message = Message(
                            id=str(uuid.uuid4()),
                            session_id=f"wa_{wa_from}",
                            channel=Channel.WHATSAPP,
                            type=MessageType.TEXT if wa_type == "text" else MessageType.TEXT,
                            text=wa_text,
                            from_user_id=wa_from,
                            company_id=company_id,  # MULTI-TENANT!
                            metadata={
                                "whatsapp_message_id": wa_message.get("id"),
                                "whatsapp_timestamp": wa_message.get("timestamp")
                            }
                        )

                        logger.info(
                            "whatsapp_message_created",
                            message_id=message.id,
                            company_id=company_id,
                            user_id=wa_from
                        )

                        # 4. TODO: Передать в AI Agent через Orchestrator
                        # await orchestrator.handle_message(message)

            return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("whatsapp_webhook_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

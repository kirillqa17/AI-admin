"""
WhatsApp Webhook Router
"""

from fastapi import APIRouter, Request, HTTPException, Query
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/webhook")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Верификация webhook для WhatsApp Business API
    
    Facebook/WhatsApp требует GET запрос для верификации
    """
    # TODO: проверить verify_token
    logger.info("whatsapp_verification_request", mode=hub_mode)
    
    if hub_mode == "subscribe":
        return int(hub_challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    Webhook для WhatsApp Business API
    
    Принимает сообщения от WhatsApp
    """
    try:
        payload = await request.json()
        
        logger.info("whatsapp_message_received", payload=payload)
        
        # TODO: Обработка WhatsApp payload
        # Извлечь сообщение
        # Преобразовать в Message
        # Передать в AI Agent
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error("whatsapp_webhook_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

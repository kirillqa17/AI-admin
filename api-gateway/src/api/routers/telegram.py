"""
Telegram Webhook Router
"""

from fastapi import APIRouter, Request, HTTPException
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Webhook для Telegram Bot API
    
    Принимает обновления от Telegram
    """
    try:
        update = await request.json()
        
        logger.info("telegram_update_received", update_id=update.get("update_id"))
        
        # TODO: Обработка Telegram update
        # Извлечь message/callback_query
        # Преобразовать в Message
        # Передать в AI Agent
        
        return {"ok": True}
        
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

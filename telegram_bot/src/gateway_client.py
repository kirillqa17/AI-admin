"""
HTTP клиент для взаимодействия с API Gateway
"""

import logging
from typing import Dict, Any
import httpx
from datetime import datetime, timezone

from .config import settings

logger = logging.getLogger(__name__)


class GatewayClient:
    """Клиент для отправки сообщений в API Gateway"""

    def __init__(self):
        self.base_url = settings.api_gateway_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0
        )

    async def send_message(
        self,
        webhook_token: str,
        telegram_user_id: int,
        telegram_username: str | None,
        telegram_first_name: str | None,
        telegram_last_name: str | None,
        text: str,
        message_id: int
    ) -> Dict[str, Any]:
        """
        Отправляет сообщение в API Gateway через Telegram webhook endpoint

        Args:
            webhook_token: Токен webhook для идентификации компании
            telegram_user_id: ID пользователя в Telegram
            telegram_username: Username пользователя (может быть None)
            telegram_first_name: Имя пользователя
            telegram_last_name: Фамилия пользователя
            text: Текст сообщения
            message_id: ID сообщения в Telegram

        Returns:
            Ответ от API Gateway
        """
        # Формируем Telegram Update объект
        telegram_update = {
            "update_id": message_id,
            "message": {
                "message_id": message_id,
                "from": {
                    "id": telegram_user_id,
                    "is_bot": False,
                    "first_name": telegram_first_name or "",
                    "last_name": telegram_last_name or "",
                    "username": telegram_username or "",
                },
                "chat": {
                    "id": telegram_user_id,
                    "type": "private",
                    "username": telegram_username or "",
                    "first_name": telegram_first_name or "",
                    "last_name": telegram_last_name or "",
                },
                "date": int(datetime.now(timezone.utc).timestamp()),
                "text": text,
            }
        }

        try:
            logger.info(
                f"Отправка сообщения в API Gateway: "
                f"webhook_token={webhook_token[:8]}..., "
                f"user_id={telegram_user_id}, "
                f"text='{text[:50]}...'"
            )

            # Отправляем в Telegram webhook endpoint
            response = await self.client.post(
                f"/api/v1/telegram/webhook/{webhook_token}",
                json=telegram_update
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Успешный ответ от API Gateway: {result}")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP ошибка при отправке в API Gateway: "
                f"status={e.response.status_code}, "
                f"body={e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Ошибка при отправке в API Gateway: {e}")
            raise

    async def health_check(self) -> bool:
        """Проверяет доступность API Gateway"""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def close(self):
        """Закрывает HTTP клиент"""
        await self.client.aclose()


# Global instance
gateway_client = GatewayClient()

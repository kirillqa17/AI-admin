"""
Telegram Bot - Entry Point

Запускает Telegram бота для приема сообщений от пользователей
и отправки их в API Gateway.
"""

import asyncio
import logging
import sys

from aiogram import Bot
from aiogram.types import BotCommand

from .config import settings
from .bot import create_bot_and_dispatcher

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Главная функция"""

    logger.info("=" * 50)
    logger.info("Запуск Telegram Bot для AI-Admin")
    logger.info("=" * 50)
    logger.info(f"API Gateway URL: {settings.api_gateway_url}")
    logger.info(f"Webhook Token: {settings.webhook_token[:8] if settings.webhook_token else 'НЕ ЗАДАН'}...")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info("=" * 50)

    # Проверяем обязательные настройки
    if not settings.webhook_token:
        logger.warning(
            "\n⚠️  ВНИМАНИЕ: webhook_token не задан!\n"
            "Бот будет работать, но не сможет отправлять сообщения в API Gateway.\n"
            "Установите переменную окружения WEBHOOK_TOKEN.\n"
        )

    # Создаем бота и диспетчер
    bot, dp = create_bot_and_dispatcher()

    try:
        # Запускаем polling
        logger.info("🚀 Запуск polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа завершена пользователем")

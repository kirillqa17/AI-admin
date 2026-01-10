"""
Telegram Bot - Entry Point

Запускает Telegram бота для приема сообщений от пользователей
и отправки их в API Gateway.

Поддерживает два режима работы:
- polling: для разработки (бот сам запрашивает обновления)
- webhook: для production (Telegram отправляет обновления на сервер)
"""

import asyncio
import logging
import sys

from aiogram import Bot
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

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


async def on_startup_webhook(bot: Bot):
    """Устанавливает webhook при запуске"""
    webhook_url = f"{settings.webhook_url}{settings.webhook_path}"
    logger.info(f"Setting webhook URL: {webhook_url}")

    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook_secret,
        drop_pending_updates=True
    )

    logger.info("Webhook установлен успешно")


async def on_shutdown_webhook(bot: Bot):
    """Удаляет webhook при остановке"""
    logger.info("Удаление webhook...")
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("Webhook удален, бот остановлен")


async def run_polling():
    """Запуск в режиме polling (для разработки)"""
    logger.info("🚀 Запуск в режиме POLLING...")

    bot, dp = create_bot_and_dispatcher()

    try:
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


def run_webhook():
    """Запуск в режиме webhook (для production)"""
    logger.info("🚀 Запуск в режиме WEBHOOK...")

    bot, dp = create_bot_and_dispatcher()

    # Регистрируем startup/shutdown handlers для webhook
    dp.startup.register(on_startup_webhook)
    dp.shutdown.register(on_shutdown_webhook)

    # Создаем aiohttp приложение
    app = web.Application()

    # Настраиваем webhook handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret
    )

    # Регистрируем маршрут для webhook
    webhook_requests_handler.register(app, path=settings.webhook_path)

    # Настраиваем приложение
    setup_application(app, dp, bot=bot)

    # Запускаем сервер
    logger.info(f"Webhook server: {settings.webhook_host}:{settings.webhook_port}")
    web.run_app(
        app,
        host=settings.webhook_host,
        port=settings.webhook_port
    )


async def main():
    """Главная функция"""

    logger.info("=" * 50)
    logger.info("Запуск Telegram Bot для AI-Admin")
    logger.info("=" * 50)
    logger.info(f"API Gateway URL: {settings.api_gateway_url}")
    logger.info(f"Webhook Token: {settings.webhook_token[:8] if settings.webhook_token else 'НЕ ЗАДАН'}...")
    logger.info(f"Bot Mode: {settings.bot_mode}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info("=" * 50)

    # Проверяем обязательные настройки
    if not settings.webhook_token:
        logger.warning(
            "\n⚠️  ВНИМАНИЕ: webhook_token не задан!\n"
            "Бот будет работать, но не сможет отправлять сообщения в API Gateway.\n"
            "Установите переменную окружения WEBHOOK_TOKEN.\n"
        )

    # Выбираем режим работы
    if settings.bot_mode.lower() == "webhook":
        if not settings.webhook_url:
            logger.error(
                "❌ WEBHOOK_URL не задан!\n"
                "Для режима webhook необходимо указать WEBHOOK_URL.\n"
                "Пример: https://your-domain.com"
            )
            sys.exit(1)

        run_webhook()
    else:
        await run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа завершена пользователем")

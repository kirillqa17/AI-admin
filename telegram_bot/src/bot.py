"""
Telegram Bot handlers
"""

import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.redis import RedisStorage

from .config import settings
from .gateway_client import gateway_client

logger = logging.getLogger(__name__)


async def cmd_start(message: Message):
    """Обработчик команды /start"""
    welcome_text = (
        "👋 Здравствуйте! Я AI-администратор.\n\n"
        "Я помогу вам записаться на услуги, проконсультирую "
        "и отвечу на ваши вопросы.\n\n"
        "Просто напишите мне, чем я могу вам помочь!"
    )
    await message.answer(welcome_text)

    # Отправляем приветственное сообщение в API Gateway
    try:
        if settings.webhook_token:
            await gateway_client.send_message(
                webhook_token=settings.webhook_token,
                telegram_user_id=message.from_user.id,
                telegram_username=message.from_user.username,
                telegram_first_name=message.from_user.first_name,
                telegram_last_name=message.from_user.last_name,
                text="/start",
                message_id=message.message_id
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке /start в Gateway: {e}")


async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "📋 Доступные команды:\n\n"
        "/start - Начать диалог\n"
        "/help - Показать эту справку\n\n"
        "Просто напишите мне сообщение, и я помогу вам!"
    )
    await message.answer(help_text)


async def handle_text_message(message: Message):
    """
    Обработчик текстовых сообщений

    Отправляет сообщение в API Gateway и возвращает ответ пользователю
    """
    if not settings.webhook_token:
        await message.answer(
            "⚠️ Бот не настроен (отсутствует webhook_token). "
            "Обратитесь к администратору."
        )
        return

    try:
        # Показываем, что бот обрабатывает сообщение
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action="typing"
        )

        logger.info(
            f"Получено сообщение от пользователя {message.from_user.id}: "
            f"'{message.text}'"
        )

        # Отправляем в API Gateway
        response = await gateway_client.send_message(
            webhook_token=settings.webhook_token,
            telegram_user_id=message.from_user.id,
            telegram_username=message.from_user.username,
            telegram_first_name=message.from_user.first_name,
            telegram_last_name=message.from_user.last_name,
            text=message.text,
            message_id=message.message_id
        )

        # Проверяем наличие ответа от AI агента
        if response and "response" in response:
            ai_response = response["response"]
            logger.info(f"Ответ от AI: '{ai_response}'")
            await message.answer(ai_response)
        else:
            logger.warning(f"Неожиданный формат ответа: {response}")
            await message.answer(
                "✅ Ваше сообщение принято в обработку!"
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке вашего сообщения. "
            "Пожалуйста, попробуйте позже."
        )


def setup_handlers(dp: Dispatcher):
    """Регистрирует все handlers бота"""

    # Команды
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))

    # Текстовые сообщения
    dp.message.register(handle_text_message, F.text)


async def on_startup(bot: Bot):
    """Вызывается при запуске бота"""
    logger.info("Бот запущен")

    # Проверяем доступность API Gateway
    if await gateway_client.health_check():
        logger.info("✅ API Gateway доступен")
    else:
        logger.warning("⚠️ API Gateway недоступен")

    # Устанавливаем команды бота
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Начать диалог"),
        types.BotCommand(command="help", description="Помощь"),
    ])


async def on_shutdown(bot: Bot):
    """Вызывается при остановке бота"""
    logger.info("Бот остановлен")
    await gateway_client.close()


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    """Создает и настраивает бота и диспетчер"""

    # Создаем бота
    bot = Bot(token=settings.telegram_bot_token)

    # Создаем Redis storage для FSM (если нужно)
    try:
        storage = RedisStorage.from_url(settings.redis_url)
        logger.info(f"Используется Redis storage: {settings.redis_url}")
    except Exception as e:
        logger.warning(f"Не удалось подключиться к Redis: {e}. Используется MemoryStorage")
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()

    # Создаем диспетчер
    dp = Dispatcher(storage=storage)

    # Регистрируем handlers
    setup_handlers(dp)

    # Регистрируем startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    return bot, dp

# Telegram Bot Service для AI-Admin

Telegram бот для приема сообщений от пользователей и отправки их в API Gateway.

## Описание

Этот микросервис реализует Telegram бота, который:
- Принимает сообщения от пользователей через Telegram Bot API (polling)
- Отправляет их в API Gateway через HTTP
- Получает ответы от AI агента и отправляет пользователям

## Технологии

- **aiogram 3.24+** - современный async framework для Telegram Bot API
- **httpx** - async HTTP клиент для взаимодействия с API Gateway
- **Redis** - хранение состояний FSM (опционально)
- **Pydantic** - валидация конфигурации

## Установка и запуск

### Через Docker (рекомендуется)

1. Создайте `.env` файл:
```bash
cp .env.example .env
```

2. Отредактируйте `.env`:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
WEBHOOK_TOKEN=your_company_webhook_token
API_GATEWAY_URL=http://api-gateway:8000
```

3. Запустите через Docker Compose из корня проекта:
```bash
docker-compose up telegram-bot
```

### Локальный запуск (для разработки)

1. Установите зависимости:
```bash
cd telegram_bot
pip install -r requirements.txt
```

2. Создайте `.env`:
```bash
cp .env.example .env
# Отредактируйте .env
```

3. Запустите:
```bash
python -m src.main
```

## Конфигурация

Все настройки задаются через переменные окружения:

| Переменная | Описание | По умолчанию |
|-----------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather | *обязательно* |
| `WEBHOOK_TOKEN` | Токен webhook компании для API Gateway | *обязательно* |
| `API_GATEWAY_URL` | URL API Gateway | `http://localhost:8000` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `REDIS_HOST` | Redis host для FSM storage | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_DB` | Redis database number | `1` |

## Получение TELEGRAM_BOT_TOKEN

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям (введите имя и username бота)
4. Получите токен вида `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

## Получение WEBHOOK_TOKEN

WEBHOOK_TOKEN - это токен компании для идентификации в multi-tenant системе.

В production окружении:
1. Компания регистрируется на сайте AI-Admin
2. В админ-панели подключает Telegram канал
3. Система генерирует уникальный webhook_token
4. Этот токен используется ботом для отправки сообщений

Для локального тестирования:
1. Создайте компанию в БД (см. `infrastructure/database/schema.sql`)
2. Создайте канал типа 'telegram' в таблице `company_channels`
3. Скопируйте `webhook_token` из БД в `.env`

## Архитектура

```
User (Telegram)
   ↓
Telegram Bot API
   ↓
Telegram Bot Service (этот сервис)
   ↓ HTTP POST /api/v1/telegram/webhook/{webhook_token}
API Gateway
   ↓
AI Agent (Orchestrator)
   ↓ Ответ
API Gateway
   ↓ (TODO: webhook или polling)
Telegram Bot Service
   ↓
Telegram Bot API
   ↓
User (Telegram)
```

## Команды бота

- `/start` - Начать диалог с AI агентом
- `/help` - Показать справку

## Логирование

Бот логирует все операции с уровнем детализации, заданным в `LOG_LEVEL`:
- Входящие сообщения от пользователей
- Отправку в API Gateway
- Ответы от API Gateway
- Ошибки

## Обработка ошибок

- Если API Gateway недоступен, бот сообщает пользователю об ошибке
- Если webhook_token не задан, бот предупреждает администратора
- Все ошибки логируются с traceback

## Разработка

### Структура проекта

```
telegram_bot/
├── src/
│   ├── __init__.py         - Инициализация пакета
│   ├── main.py             - Entry point, запуск бота
│   ├── bot.py              - Handlers и setup бота
│   ├── config.py           - Pydantic настройки
│   └── gateway_client.py   - HTTP клиент для API Gateway
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

### Добавление новых handlers

1. Откройте `src/bot.py`
2. Добавьте функцию-handler
3. Зарегистрируйте handler в `setup_handlers()`

Пример:
```python
async def handle_photo(message: Message):
    await message.answer("Спасибо за фото!")

def setup_handlers(dp: Dispatcher):
    # ... существующие handlers
    dp.message.register(handle_photo, F.photo)
```

## Тестирование

1. Запустите все сервисы (API Gateway, AI Agent, Redis, PostgreSQL)
2. Запустите бота
3. Найдите вашего бота в Telegram
4. Отправьте `/start`
5. Отправьте любое текстовое сообщение

Ожидаемое поведение:
- Бот отправит сообщение в API Gateway
- API Gateway определит company_id по webhook_token
- AI Agent обработает сообщение
- Бот получит ответ и отправит пользователю

## Production Deployment

Для production рекомендуется:

1. Использовать webhooks вместо polling (требует HTTPS):
```python
# В main.py заменить polling на webhook setup
await bot.set_webhook(settings.webhook_url)
```

2. Запускать несколько инстансов бота за load balancer

3. Использовать Redis для FSM storage (уже поддерживается)

4. Настроить мониторинг и alerting

## Troubleshooting

**Бот не запускается:**
- Проверьте `TELEGRAM_BOT_TOKEN` в `.env`
- Проверьте, что токен валиден через @BotFather

**Бот не отправляет сообщения в Gateway:**
- Проверьте `WEBHOOK_TOKEN` в `.env`
- Проверьте, что API Gateway запущен и доступен
- Проверьте логи бота

**Ошибка "webhook_token не задан":**
- Установите `WEBHOOK_TOKEN` в `.env`
- Создайте компанию и канал в БД

## Лицензия

(TBD)

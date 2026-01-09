# Конфигурация AI-Admin

Это руководство объясняет, как настроить переменные окружения для AI-Admin.

## Для запуска через Docker Compose (рекомендуется)

### ✅ Используйте ОДИН файл: `.env` в корне проекта

```bash
# 1. Скопируйте пример
cp .env.example .env

# 2. Отредактируйте .env и заполните:
nano .env
```

**Обязательные переменные:**
- `GEMINI_API_KEY` - ключ от Google Gemini API
- `TELEGRAM_BOT_TOKEN` - токен от @BotFather
- `WEBHOOK_TOKEN` - токен для тестирования (по умолчанию: `test-webhook-token-123`)

**Все остальные переменные** уже настроены для работы с Docker Compose!

### Как это работает

Docker Compose автоматически читает `.env` файл из корня проекта и прокидывает нужные переменные в каждый контейнер:

```yaml
# docker-compose.yml
services:
  telegram_bot:
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}  # ← Читается из корневого .env
      - WEBHOOK_TOKEN=${WEBHOOK_TOKEN}            # ← Читается из корневого .env
      - API_GATEWAY_URL=http://api_gateway:8000   # ← Для Docker network
```

## Для локальной разработки БЕЗ Docker

Если вы хотите запускать сервисы локально без Docker:

### 1. Создайте .env в каждом сервисе

```bash
# Для Telegram Bot
cd telegram_bot
cp .env.example .env
nano .env  # Заполните переменные

# Для AI Agent
cd ../ai_agent
cp .env.example .env
nano .env  # Заполните переменные

# И т.д. для каждого сервиса
```

### 2. Запустите инфраструктуру через Docker

```bash
# Только Redis и PostgreSQL
docker compose up -d redis postgres
```

### 3. Запустите сервисы локально

```bash
# Terminal 1: AI Agent
cd ai_agent
python -m src.main

# Terminal 2: API Gateway
cd api_gateway
uvicorn src.main:app --reload

# Terminal 3: Telegram Bot
cd telegram_bot
python -m src.main
```

## Структура .env файлов

```
AI-Admin/
├── .env                    ← ✅ ГЛАВНЫЙ файл для Docker Compose
├── .env.example            ← Шаблон с комментариями
│
├── telegram_bot/
│   └── .env.example        ← Только для локальной разработки
│
├── ai_agent/
│   └── .env.example        ← Только для локальной разработки
│
└── api_gateway/
    └── .env.example        ← Только для локальной разработки
```

## Приоритет переменных окружения

1. **Docker Compose**: Переменные из `docker-compose.yml` (environment секция)
2. **Корневой .env**: Если не указаны в docker-compose.yml
3. **Локальные .env**: Только при запуске БЕЗ Docker

## Примеры

### Полный .env для Docker Compose

```env
# Обязательные
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXX
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
WEBHOOK_TOKEN=test-webhook-token-123

# Опциональные (уже настроены)
LOG_LEVEL=INFO
CRM_TYPE=bitrix24
CRM_API_KEY=dummy_for_testing
```

### Минимальный .env для тестирования

```env
GEMINI_API_KEY=ваш_ключ
TELEGRAM_BOT_TOKEN=ваш_токен
WEBHOOK_TOKEN=test-webhook-token-123
```

Остальные переменные подставятся автоматически из docker-compose.yml.

## Безопасность

⚠️ **ВАЖНО:**
- `.env` файл добавлен в `.gitignore` и НЕ должен попадать в Git
- `.env.example` файлы безопасно коммитить в Git (они не содержат секретов)
- В production используйте secrets management (Docker Secrets, Kubernetes Secrets, AWS Secrets Manager, etc.)

## Troubleshooting

### Проблема: "TELEGRAM_BOT_TOKEN is not set"

**Решение:** Проверьте, что в корневом `.env` файле есть строка:
```env
TELEGRAM_BOT_TOKEN=ваш_реальный_токен
```

### Проблема: Telegram Bot не может подключиться к API Gateway

**Решение:** При использовании Docker Compose используйте имя сервиса:
```env
API_GATEWAY_URL=http://api_gateway:8000  # ← Для Docker
# НЕ localhost:8000
```

Для локальной разработки:
```env
API_GATEWAY_URL=http://localhost:8000  # ← Для локальной разработки
```

### Проблема: Изменения в .env не применяются

**Решение:** Пересоздайте контейнеры:
```bash
docker compose down
docker compose up --build
```

## См. также

- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Пошаговая инструкция по тестированию
- [QUICKSTART.md](QUICKSTART.md) - Быстрый старт
- [CLAUDE.md](CLAUDE.md) - Полное руководство для разработчиков

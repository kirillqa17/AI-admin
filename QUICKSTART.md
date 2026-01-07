# AI-Admin - Быстрый старт

## Предварительные требования

- Docker и Docker Compose
- Google Gemini API ключ ([получить](https://ai.google.dev/))
- CRM API ключ (Битрикс24, YCLIENTS, или другая)

## Установка и запуск

### 1. Клонирование и настройка

```bash
# Создайте .env файл из примера
cp .env.example .env

# Отредактируйте .env и добавьте свои ключи
nano .env
```

### 2. Настройка .env

```env
# Google Gemini API
GEMINI_API_KEY=your_actual_gemini_api_key

# CRM Configuration  
CRM_TYPE=bitrix24
CRM_API_KEY=your_crm_api_key
CRM_BASE_URL=https://your-company.bitrix24.ru
```

### 3. Запуск через Docker Compose

```bash
# Сборка и запуск всех сервисов
docker-compose up --build

# Или в фоновом режиме
docker-compose up -d --build
```

### 4. Проверка работы

```bash
# Health check API Gateway
curl http://localhost:8000/health

# Отправка тестового сообщения
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "user_id": "user-456",
    "channel": "web",
    "text": "Здравствуйте, хочу записаться на стрижку",
    "user_name": "Иван"
  }'
```

## Архитектура

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Telegram   │────▶│              │     │             │
│  WhatsApp   │────▶│ API Gateway  │────▶│  AI Agent   │
│  Voice      │────▶│  (FastAPI)   │     │ (Gemini)    │
│  Web        │────▶│              │     │             │
└─────────────┘     └──────────────┘     └──────┬──────┘
                            │                    │
                            │                    │
                    ┌───────▼────────┐    ┌──────▼──────┐
                    │     Redis      │    │     CRM     │
                    │   (Sessions)   │    │  (Битрикс24)│
                    └────────────────┘    └─────────────┘
```

## Сервисы

- **API Gateway**: http://localhost:8000
- **Redis**: localhost:6379
- **PostgreSQL**: localhost:5432

## Остановка

```bash
# Остановка сервисов
docker-compose down

# Остановка с удалением volumes
docker-compose down -v
```

## Разработка

### Запуск без Docker (для разработки)

#### 1. Установка зависимостей

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt
pip install -r ai-agent/requirements.txt
pip install -r api-gateway/requirements.txt
```

#### 2. Запуск Redis и PostgreSQL

```bash
docker-compose up redis postgres
```

#### 3. Запуск AI Agent

```bash
cd ai-agent
cp .env.example .env
# Отредактируйте .env

python -m src.main
```

#### 4. Запуск API Gateway (в новом терминале)

```bash
cd api-gateway
cp .env.example .env
# Отредактируйте .env

uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Следующие шаги

1. **Настройка CRM интеграции**: См. `docs/CRM_INTEGRATION.md`
2. **Настройка Telegram бота**: См. `telegram-bot/README.md`
3. **Настройка WhatsApp**: См. `whatsapp-handler/README.md`
4. **Кастомизация промптов**: См. `ai-agent/src/prompts/system_prompts.py`

## Поддержка

- Документация: `CLAUDE.md`
- Архитектура: `docs/architecture.mmd`
- Issues: создайте issue в репозитории

## Лицензия

(TBD)

# AI-Admin API Reference

> Полная документация всех API эндпоинтов системы AI-Admin

**Base URLs:**
- **API Gateway**: `http://localhost:8000`
- **AI Agent** (internal): `http://localhost:8001`

---

## API Gateway Endpoints

### Health Check

#### `GET /health/`

Проверка состояния всех сервисов.

**Response:**
```json
{
  "status": "healthy | degraded",
  "version": "1.0.0",
  "services": {
    "api_gateway": true,
    "redis": true,
    "postgres": true,
    "gemini": true
  },
  "timestamp": "2026-01-11T12:00:00Z"
}
```

**Status Codes:**
- `200` - OK

---

### Messages

#### `POST /api/v1/messages/`

Универсальный эндпоинт для обработки сообщений от любых каналов.

**Headers:**
```
Content-Type: application/json
X-API-Key: <api_key> (required)
```

**Request Body:**
```json
{
  "session_id": "string (required)",
  "user_id": "string (required)",
  "channel": "telegram | whatsapp | voice | web (required)",
  "text": "string (required)",
  "user_name": "string (optional)",
  "metadata": {
    "any": "additional data"
  }
}
```

**Response:**
```json
{
  "session_id": "sess_123",
  "message_id": "msg_456",
  "text": "Ответ AI агента",
  "state": "GREETING | COLLECTING_INFO | CONSULTING | BOOKING | CONFIRMING | COMPLETED",
  "context": {
    "name": "Иван",
    "phone": "+79001234567",
    "desired_service": "Стрижка"
  },
  "function_called": false,
  "timestamp": "2026-01-11T12:00:00Z"
}
```

**Status Codes:**
- `200` - Success
- `401` - Unauthorized (missing/invalid API key)
- `429` - Rate limit exceeded
- `500` - Internal server error

---

### Telegram Webhook

#### `POST /api/v1/telegram/webhook/{webhook_token}`

Webhook для приема обновлений от Telegram Bot API. URL содержит уникальный токен компании для multi-tenant идентификации.

**Path Parameters:**
- `webhook_token` (required) - Уникальный токен канала компании

**Request Body (from Telegram):**
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 1,
    "from": {
      "id": 123456789,
      "is_bot": false,
      "first_name": "Иван",
      "last_name": "Иванов",
      "username": "ivan"
    },
    "chat": {
      "id": 123456789,
      "type": "private"
    },
    "date": 1704931200,
    "text": "Здравствуйте, хочу записаться на стрижку"
  }
}
```

**Response:**
```json
{
  "ok": true,
  "response": "Здравствуйте! Я помогу вам записаться. Какую услугу вы хотите?",
  "function_called": false,
  "message_id": "msg_abc123"
}
```

**Error Response:**
```json
{
  "ok": false,
  "response": "Извините, произошла ошибка при обработке сообщения.",
  "error": "Error description"
}
```

**Status Codes:**
- `200` - Success
- `403` - Channel inactive
- `404` - Channel not found
- `500` - Internal server error

---

#### `GET /api/v1/telegram/webhook`

Информация о Telegram webhook.

**Response:**
```json
{
  "status": "active",
  "description": "Telegram webhook endpoint"
}
```

---

### WhatsApp Webhook

#### `GET /api/v1/whatsapp/webhook/{webhook_token}`

Верификация webhook для WhatsApp Business API. Facebook/WhatsApp требует GET запрос для верификации.

**Path Parameters:**
- `webhook_token` (required) - Уникальный токен канала компании

**Query Parameters:**
- `hub.mode` - Режим (должен быть "subscribe")
- `hub.challenge` - Challenge для верификации
- `hub.verify_token` - Токен верификации

**Response:**
- `200` + challenge value (integer) - при успешной верификации
- `403` - Verification failed
- `404` - Channel not found

---

#### `POST /api/v1/whatsapp/webhook/{webhook_token}`

Webhook для приема сообщений от WhatsApp Business API.

**Path Parameters:**
- `webhook_token` (required) - Уникальный токен канала компании

**Request Body (from WhatsApp):**
```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "PHONE_NUMBER",
              "phone_number_id": "PHONE_NUMBER_ID"
            },
            "contacts": [
              {
                "profile": { "name": "Иван" },
                "wa_id": "79001234567"
              }
            ],
            "messages": [
              {
                "from": "79001234567",
                "id": "wamid.xxx",
                "timestamp": "1704931200",
                "type": "text",
                "text": {
                  "body": "Здравствуйте, хочу записаться"
                }
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

**Response:**
```json
{
  "status": "success"
}
```

**Status Codes:**
- `200` - Success
- `403` - Channel inactive
- `404` - Channel not found
- `500` - Internal server error

---

### History & Analytics

#### `GET /api/v1/history/sessions`

Получить список сессий компании с пагинацией.

**Headers:**
```
X-API-Key: <api_key> (required)
```

**Query Parameters:**
- `company_id` (required) - ID компании
- `page` (default: 1) - Номер страницы
- `per_page` (default: 50, max: 100) - Записей на страницу
- `channel` - Фильтр по каналу (telegram, whatsapp, voice, web)
- `state` - Фильтр по состоянию (INITIATED, GREETING, BOOKING, COMPLETED, etc.)
- `start_date` - Начало периода (ISO 8601)
- `end_date` - Конец периода (ISO 8601)

**Response:**
```json
{
  "items": [
    {
      "id": "sess_123",
      "company_id": "company_456",
      "user_id": "user_789",
      "channel": "telegram",
      "state": "COMPLETED",
      "context": {"name": "Иван", "phone": "+79001234567"},
      "crm_client_id": "client_012",
      "crm_appointment_id": "apt_345",
      "created_at": "2026-01-11T10:00:00Z",
      "last_activity_at": "2026-01-11T10:15:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 50,
  "pages": 3
}
```

---

#### `GET /api/v1/history/sessions/{session_id}`

Получить детали сессии со всеми сообщениями.

**Response:**
```json
{
  "id": "sess_123",
  "company_id": "company_456",
  "user_id": "user_789",
  "channel": "telegram",
  "state": "COMPLETED",
  "context": {"name": "Иван"},
  "messages": [
    {
      "id": "msg_001",
      "text": "Здравствуйте, хочу записаться",
      "is_from_bot": false,
      "created_at": "2026-01-11T10:00:00Z"
    },
    {
      "id": "msg_002",
      "text": "Здравствуйте! Какую услугу вы хотите?",
      "is_from_bot": true,
      "created_at": "2026-01-11T10:00:01Z"
    }
  ]
}
```

---

#### `GET /api/v1/history/messages`

Получить список сообщений с фильтрацией и пагинацией.

**Query Parameters:**
- `company_id` (required) - ID компании
- `page`, `per_page` - Пагинация
- `session_id` - Фильтр по сессии
- `channel` - Фильтр по каналу
- `start_date`, `end_date` - Фильтр по периоду

---

#### `GET /api/v1/history/analytics`

Получить аналитику по сообщениям и сессиям.

**Response:**
```json
{
  "totals": {
    "messages": 15000,
    "sessions": 500
  },
  "last_30_days": {
    "messages": 3000,
    "sessions": 120
  },
  "by_channel": {
    "messages": {"telegram": 10000, "whatsapp": 5000},
    "sessions": {"telegram": 350, "whatsapp": 150}
  },
  "sessions_by_state": {
    "COMPLETED": 400,
    "BOOKING": 50,
    "GREETING": 50
  },
  "conversion_rate_30d": 85.5,
  "generated_at": "2026-01-11T12:00:00Z"
}
```

---

#### `GET /api/v1/history/analytics/daily`

Получить ежедневную статистику по сообщениям.

**Query Parameters:**
- `company_id` (required)
- `days` (default: 30, max: 365)

**Response:**
```json
{
  "company_id": "company_123",
  "days": 30,
  "data": [
    {"date": "2026-01-01", "count": 150},
    {"date": "2026-01-02", "count": 180}
  ]
}
```

---

#### `POST /api/v1/history/cleanup`

Очистить старые данные компании (Data Retention).

**Request Body:**
```json
{
  "messages_retention_days": 365,
  "sessions_retention_days": 365
}
```

**Response:**
```json
{
  "deleted_messages": 1500,
  "deleted_sessions": 50,
  "policy_applied": {
    "messages_retention_days": 365,
    "sessions_retention_days": 365
  }
}
```

---

#### `POST /api/v1/history/cleanup/estimate`

Оценить количество данных для удаления (без фактического удаления).

---

## AI Agent Endpoints (Internal)

> Эти эндпоинты используются внутри системы и не должны быть доступны извне.

### Process Message

#### `POST /process`

Обработка сообщения AI агентом.

**Request Body:**
```json
{
  "id": "msg_123 (required)",
  "session_id": "sess_456 (required)",
  "channel": "telegram | whatsapp | voice | web (required)",
  "type": "text | audio | image | video | document (default: text)",
  "text": "Текст сообщения (optional)",
  "audio_url": "URL аудио (optional)",
  "image_url": "URL изображения (optional)",
  "file_url": "URL файла (optional)",
  "from_user_id": "user_123 (required)",
  "from_user_name": "Иван (optional)",
  "company_id": "company_uuid (required for multi-tenant)",
  "metadata": {
    "telegram_chat_id": 123456789,
    "telegram_message_id": 1
  },
  "is_from_bot": false,
  "timestamp": "2026-01-11T12:00:00Z"
}
```

**Response:**
```json
{
  "ok": true,
  "text": "Ответ AI агента на сообщение пользователя",
  "function_called": true,
  "error": null,
  "session_id": "sess_456"
}
```

**Error Response:**
```json
{
  "ok": false,
  "text": null,
  "function_called": false,
  "error": "Error description",
  "session_id": null
}
```

**Status Codes:**
- `200` - Success (check `ok` field)
- `503` - Orchestrator not initialized

---

### Health Check

#### `GET /health`

Проверка состояния AI Agent.

**Response:**
```json
{
  "status": "healthy",
  "service": "ai_agent",
  "orchestrator_ready": true
}
```

---

#### `GET /`

Корневой эндпоинт AI Agent.

**Response:**
```json
{
  "service": "AI-Admin Agent",
  "version": "1.0.0",
  "status": "running"
}
```

---

## Data Models

### Message (shared/models/message.py)

```python
class Message:
    id: str                           # Уникальный ID сообщения
    session_id: str                   # ID сессии диалога
    channel: Channel                  # telegram | whatsapp | voice | web
    type: MessageType                 # text | audio | image | video | document | location | contact
    text: Optional[str]               # Текст сообщения
    audio_url: Optional[str]          # URL аудио
    image_url: Optional[str]          # URL изображения
    file_url: Optional[str]           # URL файла
    from_user_id: str                 # ID отправителя
    from_user_name: Optional[str]     # Имя отправителя
    company_id: Optional[str]         # ID компании (multi-tenant)
    metadata: Dict[str, Any]          # Дополнительные данные
    is_from_bot: bool                 # Сообщение от бота?
    timestamp: datetime               # Время сообщения
```

### Session States

```
INITIATED        # Сессия создана
GREETING         # Приветствие пользователя
COLLECTING_INFO  # Сбор информации (имя, телефон)
CONSULTING       # Консультация по услугам
BOOKING          # Процесс записи
CONFIRMING       # Подтверждение записи
COMPLETED        # Запись завершена
FAILED           # Ошибка в процессе
```

### Session Context

```json
{
  "name": "Иван Иванов",
  "phone": "+79001234567",
  "desired_service": "Мужская стрижка",
  "selected_service_id": "service_123",
  "selected_employee_id": "emp_456",
  "selected_slot": {
    "date": "2026-01-15",
    "time": "14:00"
  },
  "crm_client_id": "client_789",
  "appointment_id": "apt_012"
}
```

---

## CRM Models

### CRMClient

```json
{
  "id": "client_123",
  "phone": "+79001234567",
  "name": "Иван Иванов",
  "email": "ivan@example.com",
  "notes": "VIP клиент",
  "tags": ["vip", "regular"],
  "custom_fields": {}
}
```

### CRMService

```json
{
  "id": "service_123",
  "title": "Мужская стрижка",
  "description": "Классическая мужская стрижка",
  "price": 1500.0,
  "duration_minutes": 60,
  "category": "Парикмахерские услуги",
  "is_active": true
}
```

### CRMEmployee

```json
{
  "id": "emp_123",
  "name": "Мария Иванова",
  "specialization": "Парикмахер",
  "services": ["service_123", "service_456"],
  "working_hours": {
    "monday": "09:00-18:00",
    "tuesday": "09:00-18:00"
  },
  "is_active": true,
  "rating": 4.8
}
```

### CRMTimeSlot

```json
{
  "slot_date": "2026-01-15",
  "slot_time": "14:00",
  "duration_minutes": 60,
  "employee_id": "emp_123",
  "service_id": "service_456",
  "is_available": true
}
```

### CRMAppointment

```json
{
  "id": "apt_123",
  "client_id": "client_456",
  "service_id": "service_789",
  "employee_id": "emp_012",
  "appointment_date": "2026-01-15",
  "appointment_time": "14:00",
  "duration_minutes": 60,
  "status": "confirmed",
  "notes": "Клиент просил мастера Ивана"
}
```

---

## Authentication

### API Key Authentication

Все внешние запросы к API Gateway должны содержать API ключ в заголовке:

```
X-API-Key: your_api_key_here
```

### Webhook Token Authentication

Telegram и WhatsApp webhooks используют уникальный токен в URL:
```
/api/v1/telegram/webhook/{webhook_token}
/api/v1/whatsapp/webhook/{webhook_token}
```

Токен привязан к конкретному каналу компании и используется для multi-tenant идентификации.

---

## Rate Limiting

API Gateway реализует rate limiting на базе Redis:

| Тип клиента | Лимит | Окно |
|-------------|-------|------|
| Default | 100 req | 1 min |
| Webhooks | 1000 req | 1 min |
| Internal | 200 req | 1 min |

При превышении лимита возвращается:
- Status: `429 Too Many Requests`
- Header: `Retry-After: <seconds>`

---

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error description",
  "status_code": 400
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing/invalid API key |
| 403 | Forbidden - Channel inactive |
| 404 | Not Found - Resource not found |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Service not ready |

---

## Examples

### cURL: Send Message

```bash
curl -X POST "http://localhost:8000/api/v1/messages/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "session_id": "user_123_session",
    "user_id": "user_123",
    "channel": "web",
    "text": "Хочу записаться на стрижку",
    "user_name": "Иван"
  }'
```

### cURL: Health Check

```bash
curl -X GET "http://localhost:8000/health/"
```

### Python: Send Message

```python
import httpx

async def send_message():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/messages/",
            headers={"X-API-Key": "your_api_key"},
            json={
                "session_id": "user_123_session",
                "user_id": "user_123",
                "channel": "web",
                "text": "Хочу записаться на стрижку"
            }
        )
        return response.json()
```

---

## OpenAPI/Swagger

FastAPI автоматически генерирует OpenAPI документацию:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

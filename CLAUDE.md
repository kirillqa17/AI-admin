# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Admin — это ИИ-агент на Python для **полной замены администраторов и хостесс в бизнесе**. Система обрабатывает клиентские взаимодействия через несколько каналов: Telegram, WhatsApp и голосовые звонки.

**Целевой рынок**: Российская Федерация
**Цель проекта**: Вывод продукта на рынок с максимально легкой интеграцией в популярные CRM-системы, используемые в РФ

**Бизнес-модель**: SAAS (Software as a Service) / Multi-tenant

### Основные функции
- Прием входящих звонков
- Общение в Telegram и WhatsApp
- Консультация клиентов
- Запись клиентов на услуги
- Работа с CRM (создание записей, проверка слотов, управление клиентской базой)

## ВАЖНО: Multi-tenant архитектура

**Это SAAS продукт для множества компаний, НЕ single-tenant приложение!**

### Как это работает:

1. **Клиент (компания)** регистрируется на сайте AI-Admin
2. В **админ-панели на сайте** клиент:
   - Выбирает свою CRM (YCLIENTS, DIKIDI, Битрикс24, 1C)
   - Указывает API ключ и другие параметры подключения к своей CRM
   - Настраивает параметры агента (название компании, часы работы, промпты)
   - Подключает каналы (Telegram бот, WhatsApp, телефония)
3. **Все настройки хранятся в PostgreSQL** привязанные к `company_id`
4. **AI Agent динамически загружает** конфигурацию CRM для каждой компании из БД

### Структура данных в БД:

```sql
companies (
  id,
  name,
  created_at,
  subscription_plan
)

company_crm_settings (
  id,
  company_id,
  crm_type,        -- 'yclients', 'dikidi', 'bitrix24', '1c'
  api_key,         -- зашифрован!
  base_url,
  additional_settings  -- JSON для CRM-специфичных настроек
)

company_agent_settings (
  id,
  company_id,
  company_description,
  working_hours,
  custom_prompts     -- JSON с кастомными промптами
)

company_channels (
  id,
  company_id,
  channel_type,      -- 'telegram', 'whatsapp', 'voice'
  is_active,
  config             -- JSON с настройками канала
)
```

### Переменные окружения (CRM_TYPE, CRM_API_KEY):

**Это только для разработки и тестирования!**

В production:
- ❌ НЕТ глобальных переменных окружения для CRM
- ✅ Каждая компания имеет свои настройки в БД
- ✅ AI Agent получает `company_id` из входящего сообщения
- ✅ AI Agent загружает CRM настройки из БД по `company_id`
- ✅ Создается CRM адаптер динамически для конкретной компании

### Изменения в архитектуре:

**Orchestrator должен:**
```python
async def handle_message(self, message: Message) -> Dict:
    # 1. Извлечь company_id из сообщения
    company_id = message.metadata.get("company_id")

    # 2. Загрузить настройки компании из БД
    company_settings = await self.db.get_company_settings(company_id)

    # 3. Создать CRM адаптер для этой компании
    crm_adapter = CRMFactory.create(
        crm_type=company_settings.crm_type,
        api_key=company_settings.crm_api_key,
        base_url=company_settings.crm_base_url
    )

    # 4. Обработать сообщение с CRM этой компании
    ...
```

**API Gateway должен:**
- Определять `company_id` из webhook URL или токена
- Добавлять `company_id` в метаданные сообщения
- Пример: `/api/v1/telegram/webhook/{company_id}` или через API token

### Популярные CRM:

Согласно исследованию рынка 2026:
- **YCLIENTS** - скорее всего самый популярный выбор клиентов
- DIKIDI - второй по популярности
- Битрикс24 - для малого/среднего бизнеса
- 1C - корпоративный сегмент

## Development Approach

При работе над этим проектом необходимо:

### Senior Developer Mindset
- Действовать как Senior разработчик с фокусом на качество и долгосрочную поддерживаемость
- Проектировать решения с учетом масштабируемости и расширяемости
- Писать чистый, понятный код с четкой структурой
- Делать задел на будущие разработки

### Research & Актуальность
**ВАЖНО**: Всегда искать актуальную информацию в интернете по:
- API популярных CRM-систем в РФ и их доступности
- Используемым фреймворкам и библиотекам (проверять актуальные версии и best practices)
- Изменениям в API внешних сервисов (Telegram, WhatsApp, Google Gemini и т.д.)

### Модульность и архитектура
- **Четкая модульная структура**: каждый компонент должен быть независимым и легко заменяемым
- **Plugin-based CRM интеграции**: каждая CRM должна быть отдельным модулем с единым интерфейсом
- **Легкая интеграция новых каналов**: архитектура должна позволять добавлять новые каналы связи без изменения ядра
- **Конфигурируемость**: максимум параметров через конфигурационные файлы и переменные окружения

### Target CRM Systems (РФ)
**Приоритетные CRM для интеграции** (по исследованию рынка РФ):

**Топ-4 (по использованию):**
1. **YCLIENTS** - лидер для салонов красоты, фитнеса, медицинских центров, СПА
2. **DIKIDI** - конкурент YClients, популярен в beauty-сегменте
3. **1C** (1С:Предприятие) - доминирующая система учета и CRM в корпоративном сегменте РФ
4. **Битрикс24** (Bitrix24) - комплексная система для малого и среднего бизнеса

**Дополнительные системы для рассмотрения:**
- **amoCRM** - популярная CRM для малого и среднего бизнеса
- **МойСклад** - для торговли и услуг
- **Planfix** - управление проектами и CRM

**ВАЖНО**: Список приоритетов может корректироваться на основе дополнительных исследований рынка и обратной связи от клиентов.

**Архитектурный подход**: разработать абстрактный CRM-адаптер интерфейс, который реализуют конкретные CRM-модули. Приоритет - начать с Топ-4 систем.

#### API Доступность (исследование январь 2026):

**YCLIENTS**:
- ✅ REST API доступен ([документация](https://yclientsru.docs.apiary.io/))
- ⚠️ Webhook: с 12.09.2022 изменилась логика - новые webhook можно добавлять только через Marketplace
- Интеграция через bearer token с правами доступа
- Поддержка: запись клиентов, управление слотами, работа с клиентской базой

**DIKIDI**:
- ⚠️ API документация ограничена, необходим контакт со службой поддержки
- Доступ через Settings -> Integration -> API Access
- Существует [неофициальный wrapper на GitHub](https://github.com/ixtora/dikidi-api)
- Поддержка Callback API для webhooks

**Битрикс24**:
- ✅ Полная [REST API документация](https://apidocs.bitrix24.ru/)
- ✅ Поддержка входящих и исходящих webhooks
- Требуется подписка Marketplace для создания webhooks
- Активно поддерживается, документация обновлена в августе 2025

**1C:Предприятие**:
- ✅ REST API через OData протокол 3.0
- Поддержка SOAP веб-сервисов
- Формат данных: JSON / Atom/XML
- Платформа 8.5 добавила поддержку REST API 2.0
- Интеграция требует настройки на стороне 1C

**Рекомендация по приоритету разработки**:
1. Битрикс24 (лучшая документация и API)
2. YCLIENTS (через Marketplace)
3. 1C (требует больше настроек)
4. DIKIDI (ограниченная документация)

## Architecture

**ВАЖНО**: Полная архитектура проекта находится в `docs/architecture.mmd` — всегда обращайтесь к этой диаграмме при проектировании новых функций или изменении существующих компонентов.

Система следует многослойной архитектуре:

### Ingestion Layer (Gateway)
- **API Gateway (FastAPI)**: Central webhook receiver for all channels
- **STT Module**: Speech-to-Text conversion (Google/Whisper) for voice calls
- **TTS Module**: Text-to-Speech synthesis (Google/ElevenLabs) for voice responses
- Receives events from Telegram API, WhatsApp Business API, and VoIP telephony providers

### Core Logic Layer
- **Orchestrator**: Main dialogue controller that manages conversation flow
  - Loads/saves conversation context from Redis
  - Coordinates between components
  - Routes requests to LLM and handles responses
- **Prompt Manager**: Manages system prompts for different conversation states
- **Tool/Function Calling Manager**: Routes LLM function calls to appropriate integrations (CRM API, etc.)

### AI Layer
- **Google Gemini API**: Primary LLM for response generation and function calling

### Data & State Layer
- **Redis**: Session state storage for conversation context
- **PostgreSQL**: Persistent storage for logs, users, and analytics

### External Integrations
- **CRM System**: REST API integration for appointment slots, bookings, and customer data

## Data Flow

### Text Messages (Telegram/WhatsApp)
1. Webhook event (JSON) → API Gateway
2. Text message → Orchestrator
3. Orchestrator loads context from Redis
4. Orchestrator requests system prompt from Prompt Manager
5. Orchestrator sends prompt + context to Gemini
6. Gemini returns response (text or function_call)
7. If function_call: Tool Manager executes → CRM/DB → returns result to Orchestrator
8. Final response → API Gateway → Channel → User

### Voice Calls
1. Incoming audio stream (RTP/WebSocket) → API Gateway
2. Audio data → STT Module → transcribed text → Orchestrator
3. (Same flow as text messages)
4. Text response → TTS Module → audio stream
5. Outgoing audio → API Gateway → VoIP provider → User

## Key Design Principles

- **Session Management**: All conversation state stored in Redis with session keys
- **Stateless API Gateway**: Gateway only handles transport, all logic in Orchestrator
- **Function Calling Pattern**: LLM decides when to call CRM tools vs. respond directly
- **Multi-modal Support**: Unified orchestrator handles both text and voice through STT/TTS modules
- **Logging**: All sessions and tool executions logged to PostgreSQL for analytics

## Working with This Project

### Before Making Changes
1. **Читайте `docs/architecture.mmd`** - понимайте, как изменение влияет на общую архитектуру
2. **Ищите актуальную документацию** - проверяйте актуальность API и библиотек через WebSearch
3. **Думайте о масштабируемости** - будет ли решение работать при 100х нагрузке?
4. **Продумывайте интерфейсы** - как другие модули будут использовать ваш код?

### When Adding New Features
- **CRM интеграция**: создавайте отдельный модуль, реализующий общий CRM-адаптер интерфейс
- **Новый канал связи**: интегрируйте через API Gateway, не трогайте Orchestrator
- **Изменение промптов**: используйте Prompt Manager, не хардкодьте промпты в коде
- **Новые функции для LLM**: добавляйте через Tool Manager с четким описанием для function calling

### Code Quality Standards
- Используйте type hints (Python 3.10+)
- Документируйте публичные API (docstrings)
- Пишите unit-тесты для бизнес-логики
- Используйте async/await для I/O операций
- Логируйте важные события с structured logging
- Храните секреты в переменных окружения, не в коде

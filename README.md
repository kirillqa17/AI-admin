# AI-Admin

ИИ-агент для полной замены администраторов и хостесс в бизнесе.

## Описание проекта

AI-Admin — это комплексная система на базе ИИ для автоматизации работы с клиентами через multiple каналы:
- Прием входящих звонков
- Общение в Telegram и WhatsApp  
- Консультация клиентов
- Запись клиентов на услуги
- Работа с CRM-системами

**Целевой рынок**: Российская Федерация  
**Архитектура**: Микросервисы (каждый компонент — независимый сервис)

## Структура проекта

```
ai-admin/
├── ai-agent/              # Ядро ИИ агента (Orchestrator + Gemini + Tool Manager)
├── api-gateway/           # Центральный API Gateway (FastAPI)
├── telegram-bot/          # Telegram бот для клиентов
├── whatsapp-handler/      # WhatsApp обработчик сообщений
├── voice-handler/         # Обработчик звонков (STT/TTS + VoIP)
├── crm-integrations/      # CRM адаптеры (YCLIENTS, DIKIDI, 1C, Битрикс24)
├── website/               # Веб-сайт для клиентов и админ-панель
├── shared/                # Общие библиотеки, модели и утилиты
└── infrastructure/        # Docker, configs, scripts, database migrations
```

## Технологический стек

- **Backend**: Python 3.10+
- **API Framework**: FastAPI
- **AI/LLM**: Google Gemini API
- **Database**: PostgreSQL (данные), Redis (сессии)
- **Message Queue**: (TBD - RabbitMQ/Redis Streams)
- **Speech**: Google STT/TTS или Whisper/ElevenLabs
- **Containerization**: Docker + Docker Compose

## Интеграции с CRM

Приоритетные CRM-системы для интеграции:
1. **YCLIENTS** - салоны красоты, фитнес, медицинские центры
2. **DIKIDI** - beauty-сегмент
3. **1C** - корпоративный сегмент
4. **Битрикс24** - малый и средний бизнес

Каждая CRM реализована как отдельный плагин с единым интерфейсом.

## Быстрый старт

(В разработке)

## Документация

Подробная архитектура проекта: [docs/architecture.mmd](docs/architecture.mmd)  
Руководство для разработчиков: [CLAUDE.md](CLAUDE.md)

## Разработка

Проект разрабатывается с учетом:
- Модульности и легкой расширяемости
- Масштабируемости под высокие нагрузки
- Чистого и понятного кода
- Актуальности используемых технологий

## Лицензия

(TBD)

# AI-Admin: Roadmap до Production

> Что осталось сделать для полноценного запуска в продакшн

**Текущий прогресс: ~82%**

---

## Критические задачи (Must Have)

### 1. Тестирование CRM адаптеров с реальными системами

**Приоритет: КРИТИЧЕСКИЙ**

| CRM | Статус кода | Тестирование | Действия |
|-----|-------------|--------------|----------|
| YCLIENTS | 100% | 0% | Получить тестовый аккаунт, проверить все методы |
| Bitrix24 | 100% | 0% | Создать тестовый портал, проверить интеграцию |
| 1C:Предприятие | 100% | 0% | Настроить тестовую базу с REST API |
| amoCRM | 100% | 0% | Получить тестовый аккаунт, настроить OAuth |
| Altegio | 100% | 0% | Проверить совместимость с YCLIENTS API |
| EasyWeek | 100% | 0% | Получить тестовый аккаунт |
| DIKIDI | 20% | 0% | **НЕТ публичного API** - связаться с поддержкой |

**Что нужно проверить для каждой CRM:**
- [ ] Аутентификация и получение токенов
- [ ] Получение списка услуг
- [ ] Получение списка сотрудников
- [ ] Получение доступных слотов
- [ ] Создание/поиск клиента
- [ ] Создание записи
- [ ] Отмена записи
- [ ] Rate limiting и обработка ошибок

---

### 2. WhatsApp Handler

**Приоритет: ВЫСОКИЙ**

**Текущий статус:** Webhook принимает сообщения, но не отправляет ответы.

**Что нужно сделать:**
- [ ] Интеграция с WhatsApp Business API для отправки сообщений
- [ ] Настройка Meta Business Manager
- [ ] Верификация бизнес-аккаунта
- [ ] Получение номера телефона WhatsApp Business
- [ ] Шаблоны сообщений (для исходящих)
- [ ] Обработка медиа-сообщений (изображения, документы)
- [ ] Callback для статусов доставки

**Примерная реализация отправки:**
```python
async def send_whatsapp_message(phone: str, text: str):
    await httpx.post(
        f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text}
        }
    )
```

---

### 3. Хранение сообщений в PostgreSQL

**Приоритет: ВЫСОКИЙ**

Сейчас история сообщений хранится только в Redis с TTL. Для аналитики и аудита нужно сохранять в PostgreSQL.

**Что нужно сделать:**
- [ ] Добавить сохранение в PostgreSQL в Orchestrator после каждого сообщения
- [ ] Создать индексы для быстрого поиска (company_id, session_id, created_at)
- [ ] API для получения истории сообщений
- [ ] Очистка старых данных (data retention policy)

---

### 4. Integration Tests

**Приоритет: ВЫСОКИЙ**

**Что нужно покрыть тестами:**
- [ ] Telegram webhook → AI Agent → Response flow
- [ ] WhatsApp webhook → AI Agent → Response flow
- [ ] CRM адаптеры (mock API)
- [ ] Multi-tenant изоляция
- [ ] Rate limiting
- [ ] Шифрование/дешифрование API ключей

---

## Важные задачи (Should Have)

### 5. Voice Handler (STT/TTS)

**Приоритет: СРЕДНИЙ**

**Компоненты:**
- [ ] Интеграция с VoIP провайдером (Twilio, Zadarma, Mango Office)
- [ ] Speech-to-Text (Google Speech API / Whisper)
- [ ] Text-to-Speech (Google TTS / ElevenLabs)
- [ ] Real-time audio streaming (WebSocket)
- [ ] Обработка прерываний пользователя

---

### 6. Admin Website

**Приоритет: СРЕДНИЙ**

**Функциональность:**
- [ ] Регистрация компаний
- [ ] Настройка CRM интеграции
- [ ] Настройка AI агента (промпты, температура)
- [ ] Управление каналами (Telegram, WhatsApp)
- [ ] Dashboard с аналитикой
- [ ] Биллинг и подписки

**Технологии (рекомендуемые):**
- Frontend: Next.js / React + TypeScript
- UI: Tailwind CSS / shadcn/ui
- Auth: NextAuth.js / Clerk

---

### 7. CI/CD Pipeline

**Приоритет: СРЕДНИЙ**

**GitHub Actions:**
- [ ] Lint (ruff, black)
- [ ] Type check (mypy)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Docker build
- [ ] Deploy to staging
- [ ] Deploy to production

---

### 8. Monitoring & Observability

**Приоритет: СРЕДНИЙ**

**Что нужно:**
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Sentry для error tracking
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Alerting (PagerDuty / Telegram)

**Ключевые метрики:**
- Количество сообщений/мин
- Время ответа AI агента
- Ошибки CRM API
- Rate limit hits
- Успешные/неуспешные записи

---

## Желательные задачи (Nice to Have)

### 9. Улучшения AI агента

- [ ] Контекст из CRM (история клиента, предпочтения)
- [ ] Персонализация ответов на основе данных клиента
- [ ] A/B тестирование промптов
- [ ] Fallback на другую LLM модель при ошибках
- [ ] Автоматическое обучение на основе фидбека

---

### 10. Дополнительные каналы

- [ ] Web Chat виджет для сайтов
- [ ] VK Bot
- [ ] Viber
- [ ] Email

---

### 11. Дополнительные CRM

- [ ] МойСклад
- [ ] Planfix
- [ ] RetailCRM
- [ ] Мегаплан

---

## Инфраструктурные требования для Production

### Минимальные требования

| Компонент | Ресурсы | Примечание |
|-----------|---------|-----------|
| API Gateway | 2 vCPU, 4GB RAM | Можно масштабировать горизонтально |
| AI Agent | 4 vCPU, 8GB RAM | Зависит от нагрузки |
| Redis | 2GB RAM | Для сессий и rate limiting |
| PostgreSQL | 4 vCPU, 8GB RAM, 100GB SSD | Зависит от объема данных |

### Рекомендуемая архитектура

```
                    ┌──────────────┐
                    │   Cloudflare │
                    │   CDN + WAF  │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │   Load       │
                    │   Balancer   │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
    │ API GW 1  │   │ API GW 2  │   │ API GW 3  │
    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                    ┌──────┴───────┐
                    │   AI Agent   │
                    │   Cluster    │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
    │   Redis   │   │ PostgreSQL│   │  Gemini   │
    │  Cluster  │   │  Primary  │   │    API    │
    └───────────┘   │ + Replica │   └───────────┘
                    └───────────┘
```

### Безопасность

**Уже реализовано:**
- [x] Шифрование API ключей CRM (Fernet AES-128)
- [x] API Key аутентификация
- [x] Rate limiting
- [x] Webhook signature verification

**Нужно добавить:**
- [ ] HTTPS везде (TLS 1.3)
- [ ] Secrets management (HashiCorp Vault / AWS Secrets Manager)
- [ ] Network policies (Kubernetes) или Security Groups (AWS)
- [ ] Regular security audits
- [ ] GDPR compliance (удаление данных по запросу)
- [ ] Backup и disaster recovery

---

## Чеклист перед запуском

### Код
- [ ] Все unit тесты проходят
- [ ] Все integration тесты проходят
- [ ] Code review пройден
- [ ] Security review пройден
- [ ] Performance testing проведен

### Инфраструктура
- [ ] Production окружение настроено
- [ ] CI/CD пайплайн работает
- [ ] Мониторинг настроен
- [ ] Алерты настроены
- [ ] Backup настроен

### Документация
- [ ] API документация актуальна
- [ ] README обновлен
- [ ] Runbook для операций создан
- [ ] Incident response план готов

### Бизнес
- [ ] Лицензионные соглашения подписаны
- [ ] Условия использования готовы
- [ ] Политика конфиденциальности готова
- [ ] Биллинг настроен
- [ ] Поддержка клиентов готова

---

## Оценка времени

| Задача | Сложность | Ориентир |
|--------|-----------|----------|
| Тестирование CRM адаптеров | Высокая | Зависит от получения доступов |
| WhatsApp Handler | Средняя | Зависит от верификации Meta |
| PostgreSQL storage | Низкая | - |
| Integration tests | Средняя | - |
| Voice Handler | Высокая | - |
| Admin Website | Высокая | - |
| CI/CD | Средняя | - |
| Monitoring | Средняя | - |

---

## Рекомендуемый порядок действий

1. **Немедленно:**
   - Получить тестовые аккаунты CRM (YCLIENTS, Bitrix24, amoCRM)
   - Начать верификацию WhatsApp Business

2. **В первую очередь:**
   - Протестировать CRM адаптеры
   - Добавить хранение сообщений в PostgreSQL
   - Написать integration тесты

3. **Во вторую очередь:**
   - Доработать WhatsApp Handler
   - Настроить CI/CD
   - Настроить мониторинг

4. **В третью очередь:**
   - Начать разработку Admin Website
   - Voice Handler (если нужен)

---

**Последнее обновление:** 2026-01-11

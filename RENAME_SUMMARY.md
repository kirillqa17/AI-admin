# Directory Renaming Summary

## ✅ Выполненные изменения

### 1. Переименованы директории
- ✅ `ai-agent` → `ai_agent`
- ✅ `api-gateway` → `api_gateway`
- ✅ `crm-integrations` → `crm_integrations`

**Причина:** Дефисы `-` не допустимы в именах Python модулей. Использование underscore `_` - стандарт PEP8.

### 2. Обновлены пути в docker-compose.yml

```yaml
services:
  ai_agent:
    build:
      context: ./ai_agent

  api_gateway:
    build:
      context: ./api_gateway
    environment:
      - AI_AGENT_URL=http://ai_agent:8001
```

### 3. Обновлены requirements.txt

**ai_agent/requirements.txt:**
```txt
-e ../shared
-e ../crm_integrations
```

**api_gateway/requirements.txt:**
```txt
-e ../shared
-e ../crm_integrations
```

### 4. Обновлены импорты в коде

**До:**
```python
from ..crm-integrations.src.factory import CRMFactory  # ❌ Ошибка!
```

**После:**
```python
from crm_integrations.src.factory import CRMFactory  # ✅ Работает!
```

**Обновленные файлы:**
- `ai_agent/src/core/orchestrator.py`
- `ai_agent/src/services/tool_manager.py`
- `ai_agent/src/main.py` (также убран `sys.path.append`)

### 5. Обновлена документация

Автоматически обновлены все упоминания в:
- `CHANGELOG.md`
- `docs/ARCHITECTURE.md`
- `README.md`
- `PROJECT_STATUS.md`
- `QUICKSTART.md`
- `Dockerfile` файлы
- `.env.example` файлы

## 🎯 Итоговая структура

```
ai-admin/
├── shared/                    ← Пакет с общими моделями
├── crm_integrations/          ← Пакет с CRM адаптерами
├── ai_agent/                  ← AI Agent FastAPI app
├── api_gateway/               ← API Gateway FastAPI app
├── infrastructure/
├── docs/
└── docker-compose.yml
```

## 🚀 Проверка работоспособности

Теперь импорты должны работать корректно:

```python
# ✅ Работает
from crm_integrations.src.base import BaseCRMAdapter
from crm_integrations.src.factory import CRMFactory
from shared.models.message import Message
from shared.database.connection import Database
```

## 📦 Установка после переименования

```bash
# 1. Установить пакеты
cd shared && pip install -e . && cd ..
cd crm_integrations && pip install -e . && cd ..

# 2. Установить зависимости
cd ai_agent && pip install -r requirements.txt && cd ..
cd api_gateway && pip install -r requirements.txt && cd ..

# 3. Запуск
docker-compose up --build
```

## ⚠️ Важно

Если вы клонировали репозиторий ранее, удалите старые директории:
```bash
rm -rf ai-agent api-gateway crm-integrations
git pull  # Получит новые названия
```

## ✨ Что это исправило

1. **Ошибки импорта** - больше нет ошибок `from ..crm-integrations.src...`
2. **PEP8 совместимость** - названия директорий соответствуют стандарту
3. **IDE поддержка** - PyCharm, VSCode теперь правильно распознают модули
4. **Consistency** - все названия в snake_case

---

**Дата:** 2026-01-07
**Статус:** ✅ Завершено

FROM python:3.11-slim

WORKDIR /app

# Копирование shared models и CRM integrations (из корня проекта)
COPY shared /app/shared
COPY crm_integrations /app/crm_integrations

# Установка shared packages как editable
RUN pip install --no-cache-dir -e /app/shared -e /app/crm_integrations

# Копирование requirements и установка остальных зависимостей
COPY ai_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода агента
COPY ai_agent/src /app/src

# Запуск
CMD ["python", "-m", "src.main"]

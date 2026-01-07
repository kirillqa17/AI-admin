FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование shared models
COPY ../shared /app/shared

# Копирование CRM integrations
COPY ../crm-integrations /app/crm-integrations

# Копирование кода агента
COPY src /app/src

# Запуск
CMD ["python", "-m", "src.main"]

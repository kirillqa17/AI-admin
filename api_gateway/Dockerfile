FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование shared models
COPY ../shared /app/shared

# Копирование кода gateway
COPY src /app/src

# Запуск
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

WORKDIR /app

# Копирование requirements и установка зависимостей
COPY telegram_bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY telegram_bot/src/ ./src/

# Запускаем бота
CMD ["python", "-m", "src.main"]

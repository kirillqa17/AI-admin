"""
Конфигурация Telegram бота
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки Telegram бота"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Telegram Bot
    telegram_bot_token: str = Field(
        ...,
        description="Токен Telegram бота от @BotFather"
    )

    # API Gateway
    api_gateway_url: str = Field(
        default="http://localhost:8000",
        description="URL API Gateway"
    )

    # Webhook (для production)
    webhook_url: str | None = Field(
        default=None,
        description="Webhook URL для Telegram (если используется)"
    )
    webhook_token: str | None = Field(
        default=None,
        description="Webhook токен компании"
    )

    # Redis (для FSM storage)
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: str = Field(default="", description="Redis password")
    redis_db: int = Field(default=1, description="Redis database number")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @property
    def redis_url(self) -> str:
        """Собирает Redis URL из компонентов"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


# Global settings instance
settings = Settings()

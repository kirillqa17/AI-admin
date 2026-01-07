"""
Configuration management для AI Agent

Использует pydantic-settings для валидации и работы с .env файлами
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Настройки AI Agent"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Gemini API
    gemini_api_key: str = Field(..., description="Google Gemini API Key")
    gemini_model: str = Field(
        default="gemini-2.0-flash-exp",
        description="Модель Gemini для использования"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature для LLM")
    max_tokens: int = Field(default=8192, description="Максимум токенов в ответе")
    
    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: Optional[str] = Field(default=None)
    redis_db: int = Field(default=0)
    
    # PostgreSQL
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="ai_admin")
    postgres_user: str = Field(default="ai_admin")
    postgres_password: str = Field(..., description="PostgreSQL password")
    
    # CRM
    crm_type: str = Field(default="bitrix24", description="Тип CRM: yclients, dikidi, bitrix24, 1c")
    crm_api_key: str = Field(..., description="CRM API Key")
    crm_base_url: Optional[str] = Field(None, description="Base URL для CRM")
    
    # Session & Context
    session_ttl: int = Field(default=86400, description="TTL сессии в секундах")
    max_context_messages: int = Field(default=20, description="Макс. сообщений в контексте")
    
    # Logging
    log_level: str = Field(default="INFO", description="DEBUG, INFO, WARNING, ERROR")
    log_format: str = Field(default="json", description="json или text")
    
    # API
    ai_agent_host: str = Field(default="0.0.0.0")
    ai_agent_port: int = Field(default=8001)
    
    @property
    def redis_url(self) -> str:
        """Формирует Redis URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def postgres_url(self) -> str:
        """Формирует PostgreSQL URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# Глобальный экземпляр настроек
settings = Settings()

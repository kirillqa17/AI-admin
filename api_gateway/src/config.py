"""
Configuration для API Gateway
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """Настройки API Gateway"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # API Settings
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_title: str = Field(default="AI-Admin API Gateway")
    api_version: str = Field(default="1.0.0")
    
    # CORS
    cors_origins: str = Field(default="*")
    cors_allow_credentials: bool = Field(default=True)
    
    # AI Agent
    ai_agent_url: str = Field(default="http://localhost:8001")

    # CRM (ТОЛЬКО ДЛЯ РАЗРАБОТКИ! В production настройки в БД)
    crm_type: Optional[str] = Field(None, description="[DEV ONLY] CRM type")
    crm_api_key: Optional[str] = Field(None, description="[DEV ONLY] CRM API Key")
    crm_base_url: Optional[str] = Field(None, description="[DEV ONLY] CRM Base URL")
    
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
    
    # Gemini
    gemini_api_key: str = Field(..., description="Gemini API Key")
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    
    # Security
    api_key_secret: str = Field(..., description="Secret for API key generation")
    webhook_secret: str = Field(..., description="Secret for webhook verification")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def redis_url(self) -> str:
        """Redis URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def postgres_url(self) -> str:
        """PostgreSQL URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()

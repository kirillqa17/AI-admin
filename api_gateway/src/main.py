"""
API Gateway Main Application

Центральная точка входа для всех каналов коммуникации

Security:
- Rate limiting (Redis-based sliding window)
- API key authentication for internal endpoints
- Webhook signature verification for external integrations
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import structlog

from .config import settings
from .api.routers import message, health, telegram, whatsapp
from .middleware.rate_limit import RateLimitMiddleware

# Настройка логирования
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.log_level, logging.INFO)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="API Gateway для AI-Admin системы"
)

# Rate Limiting Middleware (должен быть первым)
app.add_middleware(
    RateLimitMiddleware,
    redis_url=settings.redis_url,
    default_limit=100,  # 100 requests per minute
    window_seconds=60,
    enabled=settings.rate_limit_enabled
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(message.router, prefix="/api/v1/messages", tags=["Messages"])
app.include_router(telegram.router, prefix="/api/v1/telegram", tags=["Telegram"])
app.include_router(whatsapp.router, prefix="/api/v1/whatsapp", tags=["WhatsApp"])


@app.on_event("startup")
async def startup_event():
    """Событие при запуске приложения"""
    logger.info(
        "api_gateway_starting",
        version=settings.api_version,
        host=settings.api_host,
        port=settings.api_port
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Событие при остановке приложения"""
    logger.info("api_gateway_shutting_down")


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "AI-Admin API Gateway",
        "version": settings.api_version,
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )

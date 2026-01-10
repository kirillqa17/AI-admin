"""
AI Agent Main Entry Point

Запуск AI агента как HTTP сервиса
"""

import logging
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from .core.orchestrator import Orchestrator
from .config import settings
from shared.models.message import Message

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

# Global orchestrator instance
orchestrator: Optional[Orchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management для FastAPI"""
    global orchestrator

    logger.info("starting_ai_agent", config=settings.model_dump())

    # Startup
    orchestrator = Orchestrator()
    await orchestrator.initialize()
    logger.info("ai_agent_started_successfully")

    yield

    # Shutdown
    if orchestrator:
        await orchestrator.shutdown()
    logger.info("ai_agent_shutdown_complete")


# FastAPI приложение
app = FastAPI(
    title="AI-Admin Agent",
    version="1.0.0",
    description="AI Agent для обработки сообщений",
    lifespan=lifespan
)


class ProcessResponse(BaseModel):
    """Ответ на обработку сообщения"""
    ok: bool = True
    text: Optional[str] = None
    function_called: bool = False
    error: Optional[str] = None
    session_id: Optional[str] = None


@app.post("/process", response_model=ProcessResponse)
async def process_message(message: Message):
    """
    Обработка входящего сообщения

    Принимает Message от API Gateway и возвращает ответ AI агента
    """
    global orchestrator

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        logger.info(
            "processing_message",
            message_id=message.id,
            company_id=message.company_id,
            channel=message.channel
        )

        result = await orchestrator.handle_message(message)

        logger.info(
            "message_processed",
            message_id=message.id,
            has_response=bool(result.get("text"))
        )

        return ProcessResponse(
            ok=True,
            text=result.get("text"),
            function_called=result.get("function_called", False),
            session_id=result.get("session_id")
        )

    except Exception as e:
        logger.error("process_message_error", error=str(e), exc_info=True)
        return ProcessResponse(
            ok=False,
            error=str(e)
        )


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": "ai_agent",
        "orchestrator_ready": orchestrator is not None
    }


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "AI-Admin Agent",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.ai_agent_host,
        port=settings.ai_agent_port,
        reload=False
    )

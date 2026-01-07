"""
AI Agent FastAPI Application

REST API для обработки сообщений через Orchestrator
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from shared.models.message import Message
from .core.orchestrator import Orchestrator
from .config import settings

# Настройка логирования
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(structlog.stdlib, settings.log_level, structlog.stdlib.INFO)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global orchestrator instance
orchestrator: Orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    global orchestrator

    logger.info("starting_ai_agent")

    # Создаем Orchestrator
    orchestrator = Orchestrator(database_url=settings.postgres_url)
    await orchestrator.initialize()

    logger.info("ai_agent_ready")

    yield

    # Shutdown
    logger.info("shutting_down_ai_agent")
    if orchestrator:
        await orchestrator.shutdown()


# Create FastAPI app
app = FastAPI(
    title="AI-Admin Agent",
    version="1.0.0",
    description="AI Agent для обработки диалогов с клиентами",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-agent",
        "version": "1.0.0"
    }


@app.post("/process")
async def process_message(message: Message):
    """
    Обработать сообщение от клиента

    Args:
        message: Сообщение для обработки

    Returns:
        Ответ AI агента
    """
    logger.info(
        "processing_message",
        message_id=message.id,
        company_id=message.company_id,
        session_id=message.session_id
    )

    try:
        result = await orchestrator.handle_message(message)

        logger.info(
            "message_processed",
            message_id=message.id,
            company_id=message.company_id
        )

        return result

    except Exception as e:
        logger.error(
            "message_processing_error",
            message_id=message.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))

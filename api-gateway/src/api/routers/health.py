"""
Health Check Router
"""

from fastapi import APIRouter
import structlog
from ...models.requests import HealthResponse
from ...config import settings

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check эндпоинт
    
    Проверяет состояние всех сервисов
    """
    # TODO: добавить реальные проверки сервисов
    services = {
        "api_gateway": True,
        "redis": False,  # TODO: проверка Redis
        "postgres": False,  # TODO: проверка PostgreSQL
        "gemini": False,  # TODO: проверка Gemini API
    }
    
    status = "healthy" if all(services.values()) else "degraded"
    
    return HealthResponse(
        status=status,
        version=settings.api_version,
        services=services
    )

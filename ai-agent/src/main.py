"""
AI Agent Main Entry Point

Запуск AI агента как standalone сервиса (опционально)
"""

import asyncio
import structlog
from .core.orchestrator import Orchestrator
from .config import settings
import sys
import os

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


async def main():
    """Главная функция для standalone запуска агента"""
    logger.info("starting_ai_agent", config=settings.model_dump())
    
    try:
        # Импортируем CRM Factory
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from crm_integrations.src.factory import CRMFactory, CRMType
        
        # Создаем CRM адаптер
        crm_type = CRMType(settings.crm_type)
        crm_adapter = CRMFactory.create(
            crm_type=crm_type,
            api_key=settings.crm_api_key,
            base_url=settings.crm_base_url
        )
        
        logger.info("crm_adapter_created", crm_type=crm_type)
        
        # Создаем Orchestrator
        orchestrator = Orchestrator(
            crm_adapter=crm_adapter,
            company_context={
                "company_name": "Тестовая компания",
                "company_description": "Салон красоты",
                "working_hours": "Пн-Пт 9:00-21:00, Сб-Вс 10:00-20:00"
            }
        )
        
        await orchestrator.initialize()
        
        logger.info("ai_agent_started_successfully")
        
        # Держим агент запущенным
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("shutting_down_ai_agent")
    except Exception as e:
        logger.error("ai_agent_startup_error", error=str(e), exc_info=True)
        raise
    finally:
        if 'orchestrator' in locals():
            await orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

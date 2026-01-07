"""
Company Service - работа с настройками компаний
"""

from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from ..database.models import (
    Company,
    CompanyCRMSettings,
    CompanyAgentSettings,
    CompanyChannel,
)

logger = structlog.get_logger(__name__)


class CompanyService:
    """Сервис для работы с компаниями и их настройками"""
    
    def __init__(self, session: AsyncSession):
        """
        Args:
            session: AsyncSession from Database
        """
        self.session = session
    
    async def get_company_by_id(self, company_id: str) -> Optional[Company]:
        """Получить компанию по ID"""
        result = await self.session.execute(
            select(Company)
            .where(Company.id == company_id)
            .options(
                selectinload(Company.crm_settings),
                selectinload(Company.agent_settings),
            )
        )
        return result.scalar_one_or_none()
    
    async def get_crm_settings(self, company_id: str) -> Optional[CompanyCRMSettings]:
        """Получить CRM настройки компании"""
        result = await self.session.execute(
            select(CompanyCRMSettings).where(
                CompanyCRMSettings.company_id == company_id,
                CompanyCRMSettings.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    async def get_agent_settings(self, company_id: str) -> Optional[CompanyAgentSettings]:
        """Получить настройки агента компании"""
        result = await self.session.execute(
            select(CompanyAgentSettings).where(
                CompanyAgentSettings.company_id == company_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_channel_by_token(self, webhook_token: str) -> Optional[CompanyChannel]:
        """Получить канал по webhook токену"""
        result = await self.session.execute(
            select(CompanyChannel).where(
                CompanyChannel.webhook_token == webhook_token,
                CompanyChannel.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    async def get_company_context(self, company_id: str) -> Dict[str, Any]:
        """Получить полный контекст компании для AI агента"""
        company = await self.get_company_by_id(company_id)
        
        if not company:
            logger.error("company_not_found", company_id=company_id)
            return {}
        
        agent_settings = company.agent_settings
        
        context = {
            "company_id": str(company.id),
            "company_name": company.name,
        }
        
        if agent_settings:
            context.update({
                # Basic Info
                "company_description": agent_settings.company_description,
                "business_type": agent_settings.business_type,
                "target_audience": agent_settings.target_audience,
                "working_hours": agent_settings.working_hours,
                "address": agent_settings.address,
                "phone_display": agent_settings.phone_display,

                # Business Context
                "services_catalog": agent_settings.services_catalog or [],
                "products_catalog": agent_settings.products_catalog or [],
                "business_highlights": agent_settings.business_highlights,

                # Agent Behavior
                "greeting_message": agent_settings.greeting_message,
                "farewell_message": agent_settings.farewell_message,
                "custom_instructions": agent_settings.custom_instructions,

                # AI Settings
                "temperature": float(agent_settings.temperature) if agent_settings.temperature else 0.7,
                "max_tokens": agent_settings.max_tokens,
            })

        return context
    
    async def decrypt_api_key(self, encrypted_key: str) -> str:
        """Расшифровать API ключ CRM (TODO: реализовать реальное шифрование)"""
        # TODO: Implement real encryption
        return encrypted_key

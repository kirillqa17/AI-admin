"""
Prompt Manager Service

Управляет системными промптами для различных состояний диалога
"""

import structlog
from typing import Dict, Optional
from ..prompts.system_prompts import SystemPrompts

logger = structlog.get_logger(__name__)


class PromptManager:
    """
    Менеджер промптов для AI агента
    
    Отвечает за:
    - Получение системных промптов для разных состояний
    - Кастомизацию промптов под конкретную компанию
    - Управление контекстом компании
    """
    
    def __init__(self, company_context: Optional[Dict[str, str]] = None):
        """
        Args:
            company_context: Контекст компании (название, услуги, особенности)
        """
        self.company_context = company_context or {}
        
        logger.info(
            "prompt_manager_initialized",
            has_company_context=bool(self.company_context)
        )
    
    def get_system_prompt(
        self,
        state: str,
        session_context: Optional[Dict] = None
    ) -> str:
        """
        Получить системный промпт для текущего состояния
        
        Args:
            state: Состояние сессии (например, "GREETING", "BOOKING")
            session_context: Контекст текущей сессии
            
        Returns:
            Системный промпт
        """
        # Получаем базовый промпт для состояния
        prompt = SystemPrompts.get_system_prompt(state)
        
        # Добавляем контекст компании, если есть
        if self.company_context:
            company_info = self._format_company_context()
            prompt = f"{prompt}\n\n{company_info}"
        
        # Добавляем контекст сессии, если есть
        if session_context:
            session_info = self._format_session_context(session_context)
            prompt = f"{prompt}\n\n{session_info}"
        
        logger.debug(
            "system_prompt_generated",
            state=state,
            prompt_length=len(prompt),
            has_session_context=bool(session_context)
        )
        
        return prompt
    
    def _format_company_context(self) -> str:
        """Форматирование контекста компании для промпта"""
        parts = ["=== ИНФОРМАЦИЯ О КОМПАНИИ ==="]

        # Basic Info
        if "company_name" in self.company_context:
            parts.append(f"Название: {self.company_context['company_name']}")

        if "company_description" in self.company_context:
            parts.append(f"Описание: {self.company_context['company_description']}")

        if "business_type" in self.company_context:
            parts.append(f"Тип бизнеса: {self.company_context['business_type']}")

        if "target_audience" in self.company_context:
            parts.append(f"Целевая аудитория: {self.company_context['target_audience']}")

        if "business_highlights" in self.company_context and self.company_context['business_highlights']:
            parts.append(f"\nПреимущества и особенности:\n{self.company_context['business_highlights']}")

        # Services Catalog
        if "services_catalog" in self.company_context and self.company_context['services_catalog']:
            parts.append("\n=== НАШИ УСЛУГИ ===")
            for service in self.company_context['services_catalog']:
                service_text = f"• {service.get('name', 'Unnamed')}"
                if service.get('description'):
                    service_text += f": {service['description']}"
                if service.get('price'):
                    service_text += f" ({service['price']} руб.)"
                if service.get('duration'):
                    service_text += f" - {service['duration']} мин"
                parts.append(service_text)

        # Products Catalog
        if "products_catalog" in self.company_context and self.company_context['products_catalog']:
            parts.append("\n=== НАШИ ТОВАРЫ ===")
            for product in self.company_context['products_catalog']:
                product_text = f"• {product.get('name', 'Unnamed')}"
                if product.get('description'):
                    product_text += f": {product['description']}"
                if product.get('price'):
                    product_text += f" ({product['price']} руб.)"
                parts.append(product_text)

        # Contact Info
        parts.append("\n=== КОНТАКТНАЯ ИНФОРМАЦИЯ ===")
        if "working_hours" in self.company_context:
            parts.append(f"Часы работы: {self.company_context['working_hours']}")

        if "address" in self.company_context:
            parts.append(f"Адрес: {self.company_context['address']}")

        if "phone_display" in self.company_context:
            parts.append(f"Телефон: {self.company_context['phone_display']}")

        # Custom Instructions
        if "custom_instructions" in self.company_context and self.company_context['custom_instructions']:
            parts.append(f"\n=== ОСОБЫЕ ИНСТРУКЦИИ ДЛЯ АГЕНТА ===\n{self.company_context['custom_instructions']}")

        return "\n".join(parts)
    
    def _format_session_context(self, context: Dict) -> str:
        """Форматирование контекста сессии для промпта"""
        parts = ["Контекст текущего диалога:"]
        
        if context.get("name"):
            parts.append(f"- Имя клиента: {context['name']}")
        
        if context.get("phone"):
            parts.append(f"- Телефон клиента: {context['phone']}")
        
        if context.get("desired_service"):
            parts.append(f"- Интересующая услуга: {context['desired_service']}")
        
        if context.get("desired_date"):
            parts.append(f"- Желаемая дата: {context['desired_date']}")
        
        if context.get("selected_slot"):
            parts.append(f"- Выбранный слот: {context['selected_slot']}")
        
        if context.get("notes"):
            parts.append(f"- Заметки: {context['notes']}")
        
        return "\n".join(parts)
    
    def update_company_context(self, context: Dict[str, str]):
        """
        Обновить контекст компании
        
        Args:
            context: Новый контекст компании
        """
        self.company_context.update(context)
        logger.info("company_context_updated", keys=list(context.keys()))
    
    def get_available_states(self) -> Dict[str, str]:
        """Получить список доступных состояний"""
        return SystemPrompts.get_available_states()

"""
Tool Manager Service

Управляет инструментами (функциями) доступными для LLM через function calling
"""

import sys
import os
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, date
from google.genai.types import Tool, FunctionDeclaration
import structlog

# Добавляем путь к CRM integrations
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from crm_integrations.src.base import BaseCRMAdapter

logger = structlog.get_logger(__name__)


class ToolManager:
    """
    Менеджер инструментов для AI агента
    
    Управляет:
    - Регистрацией доступных функций
    - Выполнением function calls от LLM
    - Интеграцией с CRM через адаптеры
    """
    
    def __init__(self, crm_adapter: BaseCRMAdapter):
        """
        Args:
            crm_adapter: Адаптер для работы с CRM
        """
        self.crm_adapter = crm_adapter
        self.tools: Dict[str, Callable] = {}
        
        # Регистрируем все доступные функции
        self._register_tools()
        
        logger.info(
            "tool_manager_initialized",
            crm_type=crm_adapter.get_crm_name(),
            tools_count=len(self.tools)
        )
    
    def _register_tools(self):
        """Регистрация всех доступных инструментов"""
        self.tools = {
            "get_services": self.get_services,
            "get_service_by_id": self.get_service_by_id,
            "get_employees": self.get_employees,
            "get_available_slots": self.get_available_slots,
            "get_client_by_phone": self.get_client_by_phone,
            "create_client": self.create_client,
            "create_appointment": self.create_appointment,
            "get_client_appointments": self.get_client_appointments,
            "cancel_appointment": self.cancel_appointment,
        }
    
    def get_tools_for_gemini(self) -> List[Tool]:
        """
        Получить список инструментов в формате Gemini API
        
        Returns:
            Список Tool объектов для Gemini
        """
        function_declarations = [
            # get_services
            FunctionDeclaration(
                name="get_services",
                description="Получить список доступных услуг из CRM. Возвращает услуги с ценами, длительностью и описаниями.",
                parameters={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Категория услуг для фильтрации (опционально)"
                        }
                    },
                    "required": []
                }
            ),
            
            # get_available_slots
            FunctionDeclaration(
                name="get_available_slots",
                description="Получить доступные временные слоты для записи на услугу. Обязательно укажи service_id и даты.",
                parameters={
                    "type": "object",
                    "properties": {
                        "service_id": {
                            "type": "string",
                            "description": "ID услуги"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Начальная дата поиска в формате YYYY-MM-DD"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Конечная дата поиска в формате YYYY-MM-DD"
                        },
                        "employee_id": {
                            "type": "string",
                            "description": "ID конкретного мастера (опционально)"
                        }
                    },
                    "required": ["service_id", "start_date", "end_date"]
                }
            ),
            
            # get_client_by_phone
            FunctionDeclaration(
                name="get_client_by_phone",
                description="Найти клиента в CRM по номеру телефона. Используй это чтобы проверить, есть ли клиент в базе.",
                parameters={
                    "type": "object",
                    "properties": {
                        "phone": {
                            "type": "string",
                            "description": "Номер телефона клиента (с кодом страны, например +79001234567)"
                        }
                    },
                    "required": ["phone"]
                }
            ),
            
            # create_client
            FunctionDeclaration(
                name="create_client",
                description="Создать нового клиента в CRM. Используй когда клиента нет в базе.",
                parameters={
                    "type": "object",
                    "properties": {
                        "phone": {
                            "type": "string",
                            "description": "Телефон клиента (обязательно)"
                        },
                        "name": {
                            "type": "string",
                            "description": "Имя клиента"
                        },
                        "email": {
                            "type": "string",
                            "description": "Email клиента (опционально)"
                        }
                    },
                    "required": ["phone", "name"]
                }
            ),
            
            # create_appointment
            FunctionDeclaration(
                name="create_appointment",
                description="Создать запись на услугу. Используй ТОЛЬКО после подтверждения всех деталей с клиентом!",
                parameters={
                    "type": "object",
                    "properties": {
                        "client_id": {
                            "type": "string",
                            "description": "ID клиента в CRM"
                        },
                        "service_id": {
                            "type": "string",
                            "description": "ID услуги"
                        },
                        "employee_id": {
                            "type": "string",
                            "description": "ID мастера (опционально)"
                        },
                        "appointment_date": {
                            "type": "string",
                            "description": "Дата записи в формате YYYY-MM-DD"
                        },
                        "appointment_time": {
                            "type": "string",
                            "description": "Время записи в формате HH:MM"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Комментарии к записи (опционально)"
                        }
                    },
                    "required": ["client_id", "service_id", "appointment_date", "appointment_time"]
                }
            ),
        ]
        
        return [Tool(function_declarations=function_declarations)]
    
    async def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнить function call от LLM
        
        Args:
            function_name: Имя функции
            arguments: Аргументы функции
            
        Returns:
            Результат выполнения функции
        """
        logger.info(
            "executing_function",
            function_name=function_name,
            arguments=arguments
        )
        
        if function_name not in self.tools:
            error_msg = f"Функция '{function_name}' не найдена"
            logger.error("function_not_found", function_name=function_name)
            return {"error": error_msg}
        
        try:
            tool_func = self.tools[function_name]
            result = await tool_func(**arguments)
            
            logger.info(
                "function_executed_successfully",
                function_name=function_name,
                result_type=type(result).__name__
            )
            
            return {"result": result}
            
        except Exception as e:
            logger.error(
                "function_execution_error",
                function_name=function_name,
                error=str(e),
                exc_info=True
            )
            return {"error": str(e)}
    
    # ===== IMPLEMENTATIONS =====
    
    async def get_services(self, category: Optional[str] = None) -> List[Dict]:
        """Получить список услуг"""
        services = await self.crm_adapter.get_services(category=category, active_only=True)
        return [s.model_dump() for s in services]
    
    async def get_service_by_id(self, service_id: str) -> Optional[Dict]:
        """Получить услугу по ID"""
        service = await self.crm_adapter.get_service_by_id(service_id)
        return service.model_dump() if service else None
    
    async def get_employees(self, service_id: Optional[str] = None) -> List[Dict]:
        """Получить список сотрудников"""
        employees = await self.crm_adapter.get_employees(service_id=service_id, active_only=True)
        return [e.model_dump() for e in employees]
    
    async def get_available_slots(
        self,
        service_id: str,
        start_date: str,
        end_date: str,
        employee_id: Optional[str] = None
    ) -> List[Dict]:
        """Получить доступные слоты"""
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        slots = await self.crm_adapter.get_available_slots(
            service_id=service_id,
            start_date=start,
            end_date=end,
            employee_id=employee_id
        )
        return [s.model_dump() for s in slots]
    
    async def get_client_by_phone(self, phone: str) -> Optional[Dict]:
        """Найти клиента по телефону"""
        client = await self.crm_adapter.get_client_by_phone(phone)
        return client.model_dump() if client else None
    
    async def create_client(self, phone: str, name: str, email: Optional[str] = None) -> Dict:
        """Создать нового клиента"""
        from shared.models.crm import CRMClient
        
        client = CRMClient(phone=phone, name=name, email=email)
        created_client = await self.crm_adapter.create_client(client)
        return created_client.model_dump()
    
    async def create_appointment(
        self,
        client_id: str,
        service_id: str,
        appointment_date: str,
        appointment_time: str,
        employee_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Создать запись"""
        from shared.models.crm import CRMAppointment
        
        appt_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        appt_time = datetime.strptime(appointment_time, "%H:%M").time()
        
        appointment = CRMAppointment(
            client_id=client_id,
            service_id=service_id,
            employee_id=employee_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            duration_minutes=60,  # TODO: получать из услуги
            notes=notes
        )
        
        created = await self.crm_adapter.create_appointment(appointment)
        return created.model_dump()
    
    async def get_client_appointments(self, client_id: str) -> List[Dict]:
        """Получить записи клиента"""
        appointments = await self.crm_adapter.get_client_appointments(client_id, include_past=False)
        return [a.model_dump() for a in appointments]
    
    async def cancel_appointment(self, appointment_id: str) -> bool:
        """Отменить запись"""
        return await self.crm_adapter.cancel_appointment(appointment_id)

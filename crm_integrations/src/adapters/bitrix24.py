"""
Битрикс24 CRM Adapter

Документация API: https://apidocs.bitrix24.ru/
"""

import httpx
from typing import List, Optional
from datetime import date, time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))

from models.crm import (
    CRMClient,
    CRMEmployee,
    CRMService,
    CRMTimeSlot,
    CRMAppointment,
)
from ..base import BaseCRMAdapter


class Bitrix24Adapter(BaseCRMAdapter):
    """
    Адаптер для Битрикс24 CRM
    
    Требует:
        - api_key: Webhook URL или access token
        - base_url: URL вашего Битрикс24 портала (например, https://your-company.bitrix24.ru)
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(api_key, base_url, **kwargs)
        
        if not base_url:
            raise ValueError("base_url обязателен для Битрикс24")
        
        # Формируем URL для REST API
        self.rest_url = f"{base_url}/rest/{api_key}"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def health_check(self) -> bool:
        """Проверка доступности Битрикс24 API"""
        try:
            response = await self.client.get(f"{self.rest_url}/app.info")
            return response.status_code == 200
        except Exception:
            return False
    
    # ===== КЛИЕНТЫ =====
    
    async def get_client_by_phone(self, phone: str) -> Optional[CRMClient]:
        """
        Поиск клиента по телефону через crm.contact.list
        
        TODO: Реализовать маппинг полей Битрикс24 -> CRMClient
        """
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    async def create_client(self, client: CRMClient) -> CRMClient:
        """
        Создание контакта через crm.contact.add
        
        TODO: Реализовать маппинг CRMClient -> поля Битрикс24
        """
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    async def update_client(self, client: CRMClient) -> CRMClient:
        """Обновление контакта через crm.contact.update"""
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    # ===== УСЛУГИ =====
    
    async def get_services(
        self,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[CRMService]:
        """
        Получение услуг через crm.product.list
        
        TODO: Битрикс24 работает с товарами/услугами через crm.product.*
        """
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    async def get_service_by_id(self, service_id: str) -> Optional[CRMService]:
        """Получение услуги по ID"""
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    # ===== СОТРУДНИКИ =====
    
    async def get_employees(
        self,
        service_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[CRMEmployee]:
        """
        Получение сотрудников через user.get
        
        TODO: Маппинг пользователей Битрикс24 -> CRMEmployee
        """
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    async def get_employee_by_id(self, employee_id: str) -> Optional[CRMEmployee]:
        """Получение сотрудника по ID"""
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    # ===== СЛОТЫ =====
    
    async def get_available_slots(
        self,
        service_id: str,
        start_date: date,
        end_date: date,
        employee_id: Optional[str] = None
    ) -> List[CRMTimeSlot]:
        """
        Получение доступных слотов через calendar.* методы
        
        TODO: Битрикс24 использует календари для управления записями
        """
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    # ===== ЗАПИСИ =====
    
    async def create_appointment(self, appointment: CRMAppointment) -> CRMAppointment:
        """
        Создание записи через crm.deal.add + calendar.event.add
        
        TODO: В Битрикс24 запись = сделка (deal) + событие в календаре
        """
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    async def get_appointment_by_id(self, appointment_id: str) -> Optional[CRMAppointment]:
        """Получение записи по ID"""
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    async def cancel_appointment(self, appointment_id: str) -> bool:
        """Отмена записи"""
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    async def get_client_appointments(
        self,
        client_id: str,
        include_past: bool = False
    ) -> List[CRMAppointment]:
        """Получение записей клиента"""
        # TODO: Реализация
        raise NotImplementedError("Будет реализовано в следующей итерации")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

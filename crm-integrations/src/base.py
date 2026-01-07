"""
Базовый абстрактный класс для CRM адаптеров

Все CRM интеграции должны реализовывать этот интерфейс
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import date, time
import sys
import os

# Добавляем путь к shared модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from models.crm import (
    CRMClient,
    CRMEmployee,
    CRMService,
    CRMTimeSlot,
    CRMAppointment,
)


class BaseCRMAdapter(ABC):
    """
    Абстрактный базовый класс для всех CRM адаптеров
    
    Каждая CRM должна реализовать этот интерфейс для унификации работы
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        """
        Args:
            api_key: API ключ для доступа к CRM
            base_url: Базовый URL API (если требуется)
            **kwargs: Дополнительные параметры (специфичные для CRM)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.config = kwargs
    
    # ============================================
    # РАБОТА С КЛИЕНТАМИ
    # ============================================
    
    @abstractmethod
    async def get_client_by_phone(self, phone: str) -> Optional[CRMClient]:
        """
        Поиск клиента по номеру телефона
        
        Args:
            phone: Номер телефона клиента
            
        Returns:
            CRMClient или None если не найден
        """
        pass
    
    @abstractmethod
    async def create_client(self, client: CRMClient) -> CRMClient:
        """
        Создание нового клиента в CRM
        
        Args:
            client: Данные клиента
            
        Returns:
            CRMClient с заполненным ID
        """
        pass
    
    @abstractmethod
    async def update_client(self, client: CRMClient) -> CRMClient:
        """
        Обновление данных клиента
        
        Args:
            client: Обновленные данные клиента
            
        Returns:
            Обновленный CRMClient
        """
        pass
    
    # ============================================
    # РАБОТА С УСЛУГАМИ
    # ============================================
    
    @abstractmethod
    async def get_services(
        self,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[CRMService]:
        """
        Получение списка услуг
        
        Args:
            category: Фильтр по категории (опционально)
            active_only: Только активные услуги
            
        Returns:
            Список услуг
        """
        pass
    
    @abstractmethod
    async def get_service_by_id(self, service_id: str) -> Optional[CRMService]:
        """
        Получение услуги по ID
        
        Args:
            service_id: ID услуги
            
        Returns:
            CRMService или None
        """
        pass
    
    # ============================================
    # РАБОТА С СОТРУДНИКАМИ
    # ============================================
    
    @abstractmethod
    async def get_employees(
        self,
        service_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[CRMEmployee]:
        """
        Получение списка сотрудников
        
        Args:
            service_id: Фильтр по услуге (опционально)
            active_only: Только активные сотрудники
            
        Returns:
            Список сотрудников
        """
        pass
    
    @abstractmethod
    async def get_employee_by_id(self, employee_id: str) -> Optional[CRMEmployee]:
        """
        Получение сотрудника по ID
        
        Args:
            employee_id: ID сотрудника
            
        Returns:
            CRMEmployee или None
        """
        pass
    
    # ============================================
    # РАБОТА С РАСПИСАНИЕМ И СЛОТАМИ
    # ============================================
    
    @abstractmethod
    async def get_available_slots(
        self,
        service_id: str,
        start_date: date,
        end_date: date,
        employee_id: Optional[str] = None
    ) -> List[CRMTimeSlot]:
        """
        Получение доступных слотов для записи
        
        Args:
            service_id: ID услуги
            start_date: Начальная дата поиска
            end_date: Конечная дата поиска
            employee_id: ID конкретного сотрудника (опционально)
            
        Returns:
            Список доступных слотов
        """
        pass
    
    # ============================================
    # РАБОТА С ЗАПИСЯМИ
    # ============================================
    
    @abstractmethod
    async def create_appointment(self, appointment: CRMAppointment) -> CRMAppointment:
        """
        Создание новой записи
        
        Args:
            appointment: Данные записи
            
        Returns:
            CRMAppointment с заполненным ID
        """
        pass
    
    @abstractmethod
    async def get_appointment_by_id(self, appointment_id: str) -> Optional[CRMAppointment]:
        """
        Получение записи по ID
        
        Args:
            appointment_id: ID записи
            
        Returns:
            CRMAppointment или None
        """
        pass
    
    @abstractmethod
    async def cancel_appointment(self, appointment_id: str) -> bool:
        """
        Отмена записи
        
        Args:
            appointment_id: ID записи
            
        Returns:
            True если успешно отменено
        """
        pass
    
    @abstractmethod
    async def get_client_appointments(
        self,
        client_id: str,
        include_past: bool = False
    ) -> List[CRMAppointment]:
        """
        Получение записей клиента
        
        Args:
            client_id: ID клиента
            include_past: Включить прошедшие записи
            
        Returns:
            Список записей клиента
        """
        pass
    
    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Проверка доступности CRM API
        
        Returns:
            True если CRM доступна
        """
        pass
    
    def get_crm_name(self) -> str:
        """
        Возвращает название CRM
        
        Returns:
            Название CRM (например, "YCLIENTS", "Битрикс24")
        """
        return self.__class__.__name__.replace("Adapter", "")

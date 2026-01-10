"""
CRM data models - универсальные модели для работы с CRM
"""

from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class CRMClient(BaseModel):
    """Модель клиента в CRM"""
    
    id: Optional[str] = Field(None, description="ID в CRM")
    phone: str = Field(..., description="Телефон (основной идентификатор)")
    name: Optional[str] = Field(None, description="Имя клиента")
    email: Optional[EmailStr] = Field(None, description="Email")
    
    # Дополнительные поля
    notes: Optional[str] = Field(None, description="Заметки о клиенте")
    tags: List[str] = Field(default_factory=list, description="Теги/категории")
    
    # Метаданные
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Дополнительные данные (CRM-specific)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+79001234567",
                "name": "Иван Иванов",
                "email": "ivan@example.com",
                "tags": ["vip", "regular"]
            }
        }


class CRMEmployee(BaseModel):
    """Модель сотрудника/мастера"""
    
    id: str = Field(..., description="ID сотрудника в CRM")
    name: str = Field(..., description="Имя сотрудника")
    specialization: Optional[str] = Field(None, description="Специализация")
    services: List[str] = Field(default_factory=list, description="Список услуг которые оказывает")
    
    # Рабочее время
    working_hours: Optional[Dict[str, Any]] = Field(None, description="График работы")
    
    # Метаданные
    is_active: bool = Field(default=True)
    rating: Optional[float] = Field(None, ge=0, le=5, description="Рейтинг сотрудника")
    
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class CRMService(BaseModel):
    """Модель услуги"""
    
    id: str = Field(..., description="ID услуги в CRM")
    title: str = Field(..., description="Название услуги")
    description: Optional[str] = Field(None, description="Описание услуги")
    
    # Цена и длительность
    price: Optional[float] = Field(None, ge=0, description="Цена в рублях")
    duration_minutes: Optional[int] = Field(None, ge=0, description="Длительность в минутах")
    
    # Категория
    category: Optional[str] = Field(None, description="Категория услуги")
    
    # Доступность
    is_active: bool = Field(default=True)
    
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "service_123",
                "title": "Мужская стрижка",
                "description": "Классическая мужская стрижка",
                "price": 1500.0,
                "duration_minutes": 60,
                "category": "Парикмахерские услуги"
            }
        }


class CRMTimeSlot(BaseModel):
    """Модель временного слота для записи"""

    slot_date: date = Field(..., description="Дата")
    slot_time: time = Field(..., description="Время начала")
    duration_minutes: int = Field(..., description="Длительность слота")

    employee_id: Optional[str] = Field(None, description="ID сотрудника")
    service_id: Optional[str] = Field(None, description="ID услуги")

    is_available: bool = Field(default=True, description="Доступен ли слот")

    class Config:
        json_schema_extra = {
            "example": {
                "slot_date": "2026-01-15",
                "slot_time": "14:00",
                "duration_minutes": 60,
                "employee_id": "emp_123",
                "service_id": "service_456",
                "is_available": True
            }
        }


class CRMAppointment(BaseModel):
    """Модель записи/appointment в CRM"""
    
    id: Optional[str] = Field(None, description="ID записи в CRM")
    
    # Основные данные
    client_id: str = Field(..., description="ID клиента")
    service_id: str = Field(..., description="ID услуги")
    employee_id: Optional[str] = Field(None, description="ID сотрудника")
    
    # Время
    appointment_date: date = Field(..., description="Дата записи")
    appointment_time: time = Field(..., description="Время записи")
    duration_minutes: int = Field(..., description="Длительность")
    
    # Статус
    status: str = Field(default="confirmed", description="Статус записи: confirmed, completed, cancelled")
    
    # Комментарии
    notes: Optional[str] = Field(None, description="Комментарии к записи")
    
    # Метаданные
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "client_123",
                "service_id": "service_456",
                "employee_id": "emp_789",
                "appointment_date": "2026-01-15",
                "appointment_time": "14:00",
                "duration_minutes": 60,
                "status": "confirmed",
                "notes": "Клиент просил мастера Ивана"
            }
        }

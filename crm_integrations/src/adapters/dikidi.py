"""
DIKIDI CRM Adapter

DIKIDI - платформа для автоматизации салонов красоты и сервисного бизнеса.
Конкурент YCLIENTS в beauty-сегменте.

===========================================================================
ВАЖНО: DIKIDI НЕ ПРЕДОСТАВЛЯЕТ ПУБЛИЧНЫЙ API (исследование января 2026)
===========================================================================

Согласно официальным источникам (GetApp, SoftwareWorld), DIKIDI не имеет
открытого API для интеграции. Доступные варианты:

1. **Неофициальный wrapper**: https://github.com/ixtora/dikidi-api
   - Не поддерживается официально
   - Может перестать работать в любой момент

2. **Интеграционные платформы**:
   - Albato (https://albato.com/apps/dikidi) - no-code интеграция
   - ApiMonster - платная настройка интеграции

3. **Нативные интеграции DIKIDI**:
   - PayPal, Square, Stripe
   - Google Analytics, Meta for Business
   - Instagram, Google Maps

4. **Официальная поддержка**:
   - Обратиться в support.dikidi.net для получения API доступа
   - Возможно доступен партнерский API по запросу

ЭТОТ АДАПТЕР:
- Реализован на основе ПРЕДПОЛАГАЕМОЙ структуры API
- Требует тестирования с реальным доступом к DIKIDI API
- Может не работать без получения официального доступа

Предполагаемая структура API (на основе анализа конкурентов):
- Base URL: https://api.dikidi.net/api/v1/ (предположительно)
- Авторизация: Bearer Token
"""

import httpx
import asyncio
from typing import List, Optional, Dict, Any
from datetime import date, time, datetime
from functools import wraps
import structlog

from ..base import BaseCRMAdapter
from shared.models.crm import (
    CRMClient,
    CRMEmployee,
    CRMService,
    CRMTimeSlot,
    CRMAppointment,
)

logger = structlog.get_logger(__name__)


class DikidiAdapter(BaseCRMAdapter):
    """
    Адаптер для DIKIDI CRM

    DIKIDI - второй по популярности сервис онлайн-записи в beauty-сегменте РФ.

    ⚠️ ВНИМАНИЕ: DIKIDI НЕ ИМЕЕТ ПУБЛИЧНОГО API (по состоянию на январь 2026)

    Этот адаптер реализован на основе ПРЕДПОЛАГАЕМОЙ структуры API,
    которая может не соответствовать реальности. Для production:

    1. Обратитесь в поддержку DIKIDI (support.dikidi.net) для получения
       официального доступа к API
    2. Используйте интеграционные платформы (Albato, ApiMonster)
    3. Рассмотрите YCLIENTS как альтернативу с открытым API

    Требует:
        - api_key: API Token (после получения официального доступа)
        - company_id: ID компании в DIKIDI

    Альтернативы для интеграции:
        - Неофициальный wrapper: https://github.com/ixtora/dikidi-api
        - Albato: https://albato.com/apps/dikidi
    """

    # Предполагаемый BASE URL (требует уточнения)
    BASE_URL = "https://api.dikidi.net/api/v1"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        company_id: Optional[str] = None,
        **kwargs
    ):
        """
        Args:
            api_key: API Token
            base_url: Базовый URL API
            company_id: ID компании в DIKIDI
        """
        super().__init__(api_key, base_url or self.BASE_URL, **kwargs)

        self.company_id = company_id or kwargs.get('company_id_in_crm')

        # HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )

        logger.info(
            "dikidi_adapter_initialized",
            company_id=self.company_id,
            note="API endpoints require verification"
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Выполнение запроса к API"""
        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "dikidi_http_error",
                status_code=e.response.status_code,
                endpoint=endpoint
            )
            raise
        except Exception as e:
            logger.error("dikidi_request_error", error=str(e), endpoint=endpoint)
            raise

    # ============================================
    # РАБОТА С КЛИЕНТАМИ
    # ============================================

    async def get_client_by_phone(self, phone: str) -> Optional[CRMClient]:
        """
        Поиск клиента по номеру телефона

        TODO: Уточнить endpoint после получения документации
        """
        try:
            clean_phone = ''.join(filter(str.isdigit, phone))

            data = await self._request(
                "GET",
                f"/company/{self.company_id}/clients",
                params={"phone": clean_phone}
            )

            clients = data.get("data", [])
            if not clients:
                return None

            return self._parse_client(clients[0])

        except Exception as e:
            logger.warning("dikidi_client_search_failed", phone=phone[-4:], error=str(e))
            return None

    async def create_client(self, client: CRMClient) -> CRMClient:
        """Создание нового клиента"""
        payload = {
            "phone": client.phone,
            "name": client.name or "",
            "email": client.email or "",
            "comment": client.notes or "",
        }

        data = await self._request(
            "POST",
            f"/company/{self.company_id}/clients",
            json=payload
        )

        logger.info("dikidi_client_created", client_id=data.get("id"))
        return self._parse_client(data.get("data", data))

    async def update_client(self, client: CRMClient) -> CRMClient:
        """Обновление данных клиента"""
        if not client.id:
            raise ValueError("Client ID is required for update")

        payload = {
            "name": client.name or "",
            "phone": client.phone,
            "email": client.email or "",
            "comment": client.notes or "",
        }

        data = await self._request(
            "PUT",
            f"/company/{self.company_id}/clients/{client.id}",
            json=payload
        )

        return self._parse_client(data.get("data", data))

    def _parse_client(self, data: Dict) -> CRMClient:
        """Парсинг данных клиента"""
        return CRMClient(
            id=str(data.get("id")),
            phone=data.get("phone", ""),
            name=data.get("name"),
            email=data.get("email"),
            notes=data.get("comment"),
            custom_fields={"dikidi_data": data}
        )

    # ============================================
    # РАБОТА С УСЛУГАМИ
    # ============================================

    async def get_services(
        self,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[CRMService]:
        """Получение списка услуг"""
        params = {}
        if category:
            params["category_id"] = category

        data = await self._request(
            "GET",
            f"/company/{self.company_id}/services",
            params=params
        )

        services = []
        for item in data.get("data", []):
            if active_only and not item.get("active", True):
                continue
            services.append(self._parse_service(item))

        logger.info("dikidi_services_fetched", count=len(services))
        return services

    async def get_service_by_id(self, service_id: str) -> Optional[CRMService]:
        """Получение услуги по ID"""
        try:
            data = await self._request(
                "GET",
                f"/company/{self.company_id}/services/{service_id}"
            )
            return self._parse_service(data.get("data", data))
        except Exception:
            return None

    def _parse_service(self, data: Dict) -> CRMService:
        """Парсинг данных услуги"""
        return CRMService(
            id=str(data.get("id")),
            title=data.get("title", data.get("name", "")),
            description=data.get("description", ""),
            price=float(data.get("price", 0)),
            duration_minutes=data.get("duration"),
            category=data.get("category", {}).get("name") if isinstance(data.get("category"), dict) else data.get("category"),
            is_active=data.get("active", True),
            custom_fields={"dikidi_data": data}
        )

    # ============================================
    # РАБОТА С СОТРУДНИКАМИ
    # ============================================

    async def get_employees(
        self,
        service_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[CRMEmployee]:
        """Получение списка сотрудников"""
        params = {}
        if service_id:
            params["service_id"] = service_id

        data = await self._request(
            "GET",
            f"/company/{self.company_id}/staff",
            params=params
        )

        employees = []
        for item in data.get("data", []):
            if active_only and not item.get("active", True):
                continue
            employees.append(self._parse_employee(item))

        logger.info("dikidi_employees_fetched", count=len(employees))
        return employees

    async def get_employee_by_id(self, employee_id: str) -> Optional[CRMEmployee]:
        """Получение сотрудника по ID"""
        try:
            data = await self._request(
                "GET",
                f"/company/{self.company_id}/staff/{employee_id}"
            )
            return self._parse_employee(data.get("data", data))
        except Exception:
            return None

    def _parse_employee(self, data: Dict) -> CRMEmployee:
        """Парсинг данных сотрудника"""
        return CRMEmployee(
            id=str(data.get("id")),
            name=data.get("name", ""),
            specialization=data.get("specialization", data.get("position")),
            is_active=data.get("active", True),
            rating=float(data.get("rating", 0)) if data.get("rating") else None,
            custom_fields={"dikidi_data": data}
        )

    # ============================================
    # РАБОТА С РАСПИСАНИЕМ И СЛОТАМИ
    # ============================================

    async def get_available_slots(
        self,
        service_id: str,
        start_date: date,
        end_date: date,
        employee_id: Optional[str] = None
    ) -> List[CRMTimeSlot]:
        """Получение доступных слотов для записи"""
        params = {
            "service_id": service_id,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
        if employee_id:
            params["staff_id"] = employee_id

        data = await self._request(
            "GET",
            f"/company/{self.company_id}/available_slots",
            params=params
        )

        slots = []
        for item in data.get("data", []):
            slot_date = datetime.strptime(item.get("date"), "%Y-%m-%d").date()
            slot_time = datetime.strptime(item.get("time"), "%H:%M").time()

            slots.append(CRMTimeSlot(
                slot_date=slot_date,
                slot_time=slot_time,
                duration_minutes=item.get("duration", 60),
                employee_id=str(item.get("staff_id", "")),
                service_id=service_id,
                is_available=True
            ))

        logger.info("dikidi_slots_fetched", count=len(slots))
        return slots

    # ============================================
    # РАБОТА С ЗАПИСЯМИ
    # ============================================

    async def create_appointment(self, appointment: CRMAppointment) -> CRMAppointment:
        """Создание новой записи"""
        appointment_datetime = datetime.combine(
            appointment.appointment_date,
            appointment.appointment_time
        )

        payload = {
            "client_id": appointment.client_id,
            "service_id": appointment.service_id,
            "staff_id": appointment.employee_id,
            "datetime": appointment_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
            "comment": appointment.notes or ""
        }

        data = await self._request(
            "POST",
            f"/company/{self.company_id}/appointments",
            json=payload
        )

        record_data = data.get("data", data)
        logger.info("dikidi_appointment_created", record_id=record_data.get("id"))

        return CRMAppointment(
            id=str(record_data.get("id")),
            client_id=appointment.client_id,
            service_id=appointment.service_id,
            employee_id=appointment.employee_id,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            duration_minutes=appointment.duration_minutes,
            status="confirmed",
            notes=appointment.notes,
            custom_fields={"dikidi_data": record_data}
        )

    async def get_appointment_by_id(self, appointment_id: str) -> Optional[CRMAppointment]:
        """Получение записи по ID"""
        try:
            data = await self._request(
                "GET",
                f"/company/{self.company_id}/appointments/{appointment_id}"
            )
            return self._parse_appointment(data.get("data", data))
        except Exception:
            return None

    async def cancel_appointment(self, appointment_id: str) -> bool:
        """Отмена записи"""
        try:
            await self._request(
                "DELETE",
                f"/company/{self.company_id}/appointments/{appointment_id}"
            )
            logger.info("dikidi_appointment_cancelled", appointment_id=appointment_id)
            return True
        except Exception as e:
            logger.error("dikidi_cancel_failed", error=str(e))
            return False

    async def get_client_appointments(
        self,
        client_id: str,
        include_past: bool = False
    ) -> List[CRMAppointment]:
        """Получение записей клиента"""
        params = {"client_id": client_id}
        if not include_past:
            params["start_date"] = date.today().strftime("%Y-%m-%d")

        data = await self._request(
            "GET",
            f"/company/{self.company_id}/appointments",
            params=params
        )

        return [self._parse_appointment(item) for item in data.get("data", [])]

    def _parse_appointment(self, data: Dict) -> CRMAppointment:
        """Парсинг данных записи"""
        datetime_str = data.get("datetime", "")
        if datetime_str:
            dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            appt_date = dt.date()
            appt_time = dt.time()
        else:
            appt_date = date.today()
            appt_time = time(0, 0)

        return CRMAppointment(
            id=str(data.get("id")),
            client_id=str(data.get("client_id", "")),
            service_id=str(data.get("service_id", "")),
            employee_id=str(data.get("staff_id", "")),
            appointment_date=appt_date,
            appointment_time=appt_time,
            duration_minutes=data.get("duration", 60),
            status=data.get("status", "confirmed"),
            notes=data.get("comment"),
            custom_fields={"dikidi_data": data}
        )

    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================

    async def health_check(self) -> bool:
        """Проверка доступности DIKIDI API"""
        try:
            await self._request("GET", f"/company/{self.company_id}")
            return True
        except Exception as e:
            logger.error("dikidi_health_check_failed", error=str(e))
            return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

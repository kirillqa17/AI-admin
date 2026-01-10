"""
EasyWeek CRM Adapter

EasyWeek - платформа онлайн-записи и управления бизнесом для сферы услуг.
Используется 35,000+ бизнесами в 40+ странах.

Документация API:
- Developers Portal: https://developers.easyweek.io/
- API Documentation: https://api-doc.easyweek.io/
- GitHub: https://github.com/easyweek/api-documentation

Особенности:
- REST API с OAuth 2.0 авторизацией
- Webhooks для real-time событий
- Интеграция с Google Calendar, Telegram, WhatsApp
- Поддержка онлайн-оплаты

Сферы применения:
- Салоны красоты
- Медицинские практики
- Фото-студии
- Фитнес-центры
- Wellness-клиники

URL формат: https://my.easyweek.io/api/ext/{resource}
"""

import httpx
from typing import List, Optional, Dict, Any
from datetime import date, time, datetime, timedelta
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


class EasyWeekAdapter(BaseCRMAdapter):
    """
    Адаптер для EasyWeek

    EasyWeek - популярная международная платформа для онлайн-записи.
    Поддерживает русский язык и работает в России.

    Требует:
        - api_key: Access Token (OAuth 2.0)
        - company_id: ID компании в EasyWeek (workspace_id)

    OAuth 2.0:
        - client_id: ID приложения
        - client_secret: Secret приложения
        - redirect_uri: URI для callback

    Особенности:
        - Простая интеграция с виджетом записи
        - Поддержка многих платежных систем
        - Интеграция с мессенджерами
    """

    BASE_URL = "https://my.easyweek.io/api/ext"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        company_id: Optional[str] = None,
        **kwargs
    ):
        """
        Args:
            api_key: Access Token (OAuth 2.0)
            base_url: Базовый URL API
            company_id: ID компании/workspace в EasyWeek
        """
        super().__init__(api_key, base_url or self.BASE_URL, **kwargs)

        self.company_id = company_id or kwargs.get('company_id_in_crm') or kwargs.get('workspace_id')
        self.access_token = api_key

        # HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )

        logger.info(
            "easyweek_adapter_initialized",
            company_id=self.company_id
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

            if response.status_code == 204:
                return {}

            data = response.json()

            # EasyWeek может возвращать {"data": ..., "meta": ...}
            if isinstance(data, dict) and "data" in data:
                return data["data"]

            return data

        except httpx.HTTPStatusError as e:
            logger.error(
                "easyweek_http_error",
                status_code=e.response.status_code,
                endpoint=endpoint,
                response=e.response.text[:500] if e.response.text else None
            )
            raise
        except Exception as e:
            logger.error("easyweek_request_error", error=str(e), endpoint=endpoint)
            raise

    # ============================================
    # РАБОТА С КЛИЕНТАМИ
    # ============================================

    async def get_client_by_phone(self, phone: str) -> Optional[CRMClient]:
        """Поиск клиента по номеру телефона"""
        try:
            clean_phone = ''.join(filter(str.isdigit, phone))

            data = await self._request(
                "GET",
                "/user/clients",
                params={"phone": clean_phone}
            )

            clients = data if isinstance(data, list) else data.get("clients", [])
            if not clients:
                return None

            return self._parse_client(clients[0])

        except Exception as e:
            logger.warning("easyweek_client_search_failed", phone=phone[-4:], error=str(e))
            return None

    async def create_client(self, client: CRMClient) -> CRMClient:
        """Создание нового клиента"""
        payload = {
            "phone": client.phone,
            "name": client.name or "",
            "email": client.email or "",
            "note": client.notes or "",
        }

        data = await self._request(
            "POST",
            "/user/clients",
            json=payload
        )

        logger.info("easyweek_client_created", client_id=data.get("id"))
        return self._parse_client(data)

    async def update_client(self, client: CRMClient) -> CRMClient:
        """Обновление данных клиента"""
        if not client.id:
            raise ValueError("Client ID is required for update")

        payload = {
            "name": client.name or "",
            "phone": client.phone,
            "email": client.email or "",
            "note": client.notes or "",
        }

        data = await self._request(
            "PUT",
            f"/user/clients/{client.id}",
            json=payload
        )

        logger.info("easyweek_client_updated", client_id=client.id)
        return self._parse_client(data)

    def _parse_client(self, data: Dict) -> CRMClient:
        """Парсинг данных клиента"""
        return CRMClient(
            id=str(data.get("id")),
            phone=data.get("phone", ""),
            name=data.get("name"),
            email=data.get("email"),
            notes=data.get("note"),
            created_at=self._parse_datetime(data.get("created_at")),
            custom_fields={"easyweek_data": data}
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
            "/user/services",
            params=params
        )

        services_list = data if isinstance(data, list) else data.get("services", [])

        services = []
        for item in services_list:
            if active_only and not item.get("is_active", True):
                continue
            services.append(self._parse_service(item))

        logger.info("easyweek_services_fetched", count=len(services))
        return services

    async def get_service_by_id(self, service_id: str) -> Optional[CRMService]:
        """Получение услуги по ID"""
        try:
            data = await self._request(
                "GET",
                f"/user/services/{service_id}"
            )
            return self._parse_service(data)
        except Exception:
            return None

    def _parse_service(self, data: Dict) -> CRMService:
        """Парсинг данных услуги"""
        return CRMService(
            id=str(data.get("id")),
            title=data.get("name", data.get("title", "")),
            description=data.get("description", ""),
            price=float(data.get("price", 0)),
            duration_minutes=data.get("duration"),
            category=data.get("category", {}).get("name") if isinstance(data.get("category"), dict) else None,
            is_active=data.get("is_active", True),
            custom_fields={"easyweek_data": data}
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
            "/user/employees",
            params=params
        )

        employees_list = data if isinstance(data, list) else data.get("employees", [])

        employees = []
        for item in employees_list:
            if active_only and not item.get("is_active", True):
                continue
            employees.append(self._parse_employee(item))

        logger.info("easyweek_employees_fetched", count=len(employees))
        return employees

    async def get_employee_by_id(self, employee_id: str) -> Optional[CRMEmployee]:
        """Получение сотрудника по ID"""
        try:
            data = await self._request(
                "GET",
                f"/user/employees/{employee_id}"
            )
            return self._parse_employee(data)
        except Exception:
            return None

    def _parse_employee(self, data: Dict) -> CRMEmployee:
        """Парсинг данных сотрудника"""
        return CRMEmployee(
            id=str(data.get("id")),
            name=data.get("name", ""),
            specialization=data.get("position", data.get("specialization")),
            is_active=data.get("is_active", True),
            rating=float(data.get("rating", 0)) if data.get("rating") else None,
            custom_fields={"easyweek_data": data}
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
            "date_from": start_date.strftime("%Y-%m-%d"),
            "date_to": end_date.strftime("%Y-%m-%d"),
        }

        if employee_id:
            params["employee_id"] = employee_id

        try:
            data = await self._request(
                "GET",
                "/user/available-slots",
                params=params
            )
        except Exception as e:
            logger.warning("easyweek_slots_fetch_failed", error=str(e))
            # Генерируем слоты по умолчанию
            return self._generate_default_slots(service_id, start_date, end_date, employee_id)

        slots_list = data if isinstance(data, list) else data.get("slots", [])

        slots = []
        for item in slots_list:
            slot_date = datetime.strptime(item.get("date"), "%Y-%m-%d").date()
            slot_time = datetime.strptime(item.get("time"), "%H:%M").time()

            slots.append(CRMTimeSlot(
                slot_date=slot_date,
                slot_time=slot_time,
                duration_minutes=item.get("duration", 60),
                employee_id=str(item.get("employee_id", employee_id or "")),
                service_id=service_id,
                is_available=item.get("is_available", True)
            ))

        logger.info("easyweek_slots_fetched", count=len(slots))
        return slots

    def _generate_default_slots(
        self,
        service_id: str,
        start_date: date,
        end_date: date,
        employee_id: Optional[str] = None
    ) -> List[CRMTimeSlot]:
        """Генерация слотов по умолчанию (9:00-18:00)"""
        slots = []
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() < 6:  # Пн-Сб
                for hour in range(9, 18):
                    for minute in [0, 30]:
                        slots.append(CRMTimeSlot(
                            slot_date=current_date,
                            slot_time=time(hour, minute),
                            duration_minutes=30,
                            employee_id=employee_id,
                            service_id=service_id,
                            is_available=True
                        ))
            current_date += timedelta(days=1)

        return slots[:100]

    # ============================================
    # РАБОТА С ЗАПИСЯМИ (Bookings)
    # ============================================

    async def create_appointment(self, appointment: CRMAppointment) -> CRMAppointment:
        """Создание новой записи"""
        appointment_datetime = datetime.combine(
            appointment.appointment_date,
            appointment.appointment_time
        )

        payload = {
            "client_id": int(appointment.client_id) if appointment.client_id else None,
            "service_id": int(appointment.service_id),
            "employee_id": int(appointment.employee_id) if appointment.employee_id else None,
            "datetime": appointment_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
            "duration": appointment.duration_minutes,
            "note": appointment.notes or ""
        }

        data = await self._request(
            "POST",
            "/user/bookings",
            json=payload
        )

        booking_id = str(data.get("id"))
        logger.info("easyweek_appointment_created", booking_id=booking_id)

        return CRMAppointment(
            id=booking_id,
            client_id=appointment.client_id,
            service_id=appointment.service_id,
            employee_id=appointment.employee_id,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            duration_minutes=appointment.duration_minutes,
            status="confirmed",
            notes=appointment.notes,
            custom_fields={"easyweek_data": data}
        )

    async def get_appointment_by_id(self, appointment_id: str) -> Optional[CRMAppointment]:
        """Получение записи по ID"""
        try:
            data = await self._request(
                "GET",
                f"/user/bookings/{appointment_id}"
            )
            return self._parse_appointment(data)
        except Exception:
            return None

    async def cancel_appointment(self, appointment_id: str) -> bool:
        """Отмена записи"""
        try:
            await self._request(
                "DELETE",
                f"/user/bookings/{appointment_id}"
            )
            logger.info("easyweek_appointment_cancelled", booking_id=appointment_id)
            return True
        except Exception as e:
            logger.error("easyweek_cancel_failed", error=str(e))
            return False

    async def get_client_appointments(
        self,
        client_id: str,
        include_past: bool = False
    ) -> List[CRMAppointment]:
        """Получение записей клиента"""
        params = {"client_id": client_id}

        if not include_past:
            params["date_start"] = datetime.now().strftime("%Y-%m-%dT00:00:00")

        try:
            data = await self._request(
                "GET",
                "/user/bookings",
                params=params
            )
        except Exception as e:
            logger.warning("easyweek_get_appointments_failed", error=str(e))
            return []

        bookings = data if isinstance(data, list) else data.get("bookings", [])
        return [self._parse_appointment(item) for item in bookings]

    def _parse_appointment(self, data: Dict) -> CRMAppointment:
        """Парсинг данных записи"""
        datetime_str = data.get("datetime", data.get("start_time", ""))
        if datetime_str:
            try:
                dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                appt_date = dt.date()
                appt_time = dt.time()
            except ValueError:
                appt_date = date.today()
                appt_time = time(0, 0)
        else:
            appt_date = date.today()
            appt_time = time(0, 0)

        # Маппинг статусов
        status_raw = data.get("status", "confirmed")
        status_map = {
            "pending": "pending",
            "confirmed": "confirmed",
            "completed": "completed",
            "cancelled": "cancelled",
            "no_show": "cancelled"
        }
        status = status_map.get(status_raw, "confirmed")

        return CRMAppointment(
            id=str(data.get("id")),
            client_id=str(data.get("client_id", data.get("client", {}).get("id", ""))),
            service_id=str(data.get("service_id", data.get("service", {}).get("id", ""))),
            employee_id=str(data.get("employee_id", data.get("employee", {}).get("id", ""))),
            appointment_date=appt_date,
            appointment_time=appt_time,
            duration_minutes=data.get("duration", 60),
            status=status,
            notes=data.get("note", data.get("notes")),
            custom_fields={"easyweek_data": data}
        )

    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================

    async def health_check(self) -> bool:
        """Проверка доступности EasyWeek API"""
        try:
            await self._request("GET", "/user/profile")
            return True
        except Exception as e:
            logger.error("easyweek_health_check_failed", error=str(e))
            return False

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Парсинг даты/времени из строки"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError:
            return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

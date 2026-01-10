"""
Altegio CRM Adapter

Altegio - ребрендинг YCLIENTS с обновленным API.
Платформа для автоматизации бизнеса в сфере услуг: салоны красоты, фитнес, медицина.

Документация API:
- Официальная: https://developer.alteg.io/en
- API URL: https://api.alteg.io/api/v1/

Особенности:
- REST API (похож на YCLIENTS, но с улучшениями)
- OAuth 2.0 авторизация (Resource Owner Password Credentials Grant)
- Rate limit: 200 запросов/минуту или 5 запросов/секунду на IP
- Поддержка webhooks для real-time событий

Авторизация:
- partner_token (Bearer) - получается при регистрации в marketplace
- user_token - для операций от имени пользователя

Отличия от YCLIENTS:
- Новый домен API: api.alteg.io (вместо api.yclients.com)
- Улучшенная документация
- Больше возможностей для интеграции
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

# Rate limiter - max 5 requests per second
_last_request_time = 0
_request_interval = 0.2  # 200ms between requests


def rate_limit(func):
    """Декоратор для ограничения частоты запросов"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global _last_request_time
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - _last_request_time

        if time_since_last < _request_interval:
            await asyncio.sleep(_request_interval - time_since_last)

        _last_request_time = asyncio.get_event_loop().time()
        return await func(*args, **kwargs)
    return wrapper


class AltegioAdapter(BaseCRMAdapter):
    """
    Адаптер для Altegio (бывший YCLIENTS)

    Altegio - лидер в России для автоматизации бизнеса в сфере услуг.
    Используется салонами красоты, фитнес-клубами, медицинскими центрами.

    Требует:
        - api_key: Partner Token (Bearer token из marketplace)
        - company_id: ID компании в Altegio
        - user_token: User Token (опционально, для полного доступа)

    Преимущества перед YCLIENTS адаптером:
        - Обновленный API с лучшей документацией
        - Поддержка webhooks
        - Больше методов для интеграции
    """

    BASE_URL = "https://api.alteg.io/api/v1"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        company_id: Optional[str] = None,
        user_token: Optional[str] = None,
        **kwargs
    ):
        """
        Args:
            api_key: Partner Token (Bearer token)
            base_url: Базовый URL API (по умолчанию https://api.alteg.io/api/v1)
            company_id: ID компании в Altegio
            user_token: User Token для расширенного доступа
        """
        super().__init__(api_key, base_url or self.BASE_URL, **kwargs)

        self.company_id = company_id or kwargs.get('company_id_in_crm')
        self.user_token = user_token
        self.partner_token = api_key

        # HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers=self._get_headers()
        )

        logger.info(
            "altegio_adapter_initialized",
            company_id=self.company_id,
            has_user_token=bool(self.user_token)
        )

    def _get_headers(self) -> Dict[str, str]:
        """Формирование заголовков для запросов"""
        headers = {
            "Accept": "application/vnd.api.v2+json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.partner_token}"
        }

        if self.user_token:
            headers["Authorization"] += f", User {self.user_token}"

        return headers

    @rate_limit
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

            data = response.json()

            # Altegio возвращает {"success": true, "data": ..., "meta": ...}
            if isinstance(data, dict) and "success" in data:
                if not data.get("success"):
                    error_msg = data.get("meta", {}).get("message", "Unknown error")
                    logger.error("altegio_api_error", error=error_msg)
                    raise Exception(f"Altegio API error: {error_msg}")
                return data.get("data", data)

            return data

        except httpx.HTTPStatusError as e:
            logger.error(
                "altegio_http_error",
                status_code=e.response.status_code,
                endpoint=endpoint
            )
            raise
        except Exception as e:
            logger.error("altegio_request_error", error=str(e), endpoint=endpoint)
            raise

    # ============================================
    # АВТОРИЗАЦИЯ
    # ============================================

    async def authenticate(self, login: str, password: str) -> str:
        """
        Получение user_token через логин/пароль

        Args:
            login: Email или телефон
            password: Пароль

        Returns:
            User token
        """
        data = await self._request(
            "POST",
            "/auth",
            json={"login": login, "password": password}
        )

        self.user_token = data.get("user_token")
        self.client.headers.update(self._get_headers())

        logger.info("altegio_authenticated", user_id=data.get("id"))
        return self.user_token

    # ============================================
    # РАБОТА С КЛИЕНТАМИ
    # ============================================

    async def get_client_by_phone(self, phone: str) -> Optional[CRMClient]:
        """Поиск клиента по номеру телефона"""
        try:
            clean_phone = ''.join(filter(str.isdigit, phone))

            data = await self._request(
                "GET",
                f"/company/{self.company_id}/clients/search",
                params={"phone": clean_phone}
            )

            if not data:
                return None

            client_data = data[0] if isinstance(data, list) else data
            return self._parse_client(client_data)

        except Exception as e:
            logger.warning("altegio_client_search_failed", phone=phone[-4:], error=str(e))
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

        logger.info("altegio_client_created", client_id=data.get("id"))
        return self._parse_client(data)

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
            f"/company/{self.company_id}/client/{client.id}",
            json=payload
        )

        logger.info("altegio_client_updated", client_id=client.id)
        return self._parse_client(data)

    def _parse_client(self, data: Dict) -> CRMClient:
        """Парсинг данных клиента"""
        return CRMClient(
            id=str(data.get("id")),
            phone=data.get("phone", ""),
            name=data.get("name"),
            email=data.get("email"),
            notes=data.get("comment"),
            created_at=self._parse_datetime(data.get("created_date")),
            custom_fields={"altegio_data": data}
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
        for item in data if isinstance(data, list) else [data]:
            # Altegio возвращает услуги сгруппированные по категориям
            if "services" in item:
                category_name = item.get("title", "")
                for service in item.get("services", []):
                    if active_only and not service.get("active", True):
                        continue
                    services.append(self._parse_service(service, category_name))
            else:
                if active_only and not item.get("active", True):
                    continue
                services.append(self._parse_service(item))

        logger.info("altegio_services_fetched", count=len(services))
        return services

    async def get_service_by_id(self, service_id: str) -> Optional[CRMService]:
        """Получение услуги по ID"""
        try:
            data = await self._request(
                "GET",
                f"/company/{self.company_id}/services/{service_id}"
            )
            return self._parse_service(data)
        except Exception:
            return None

    def _parse_service(self, data: Dict, category: Optional[str] = None) -> CRMService:
        """Парсинг данных услуги"""
        return CRMService(
            id=str(data.get("id")),
            title=data.get("title", ""),
            description=data.get("comment", ""),
            price=float(data.get("price_min", 0) or data.get("price", 0)),
            duration_minutes=int(data.get("duration", 0) / 60) if data.get("duration") else None,
            category=category or data.get("category", {}).get("title"),
            is_active=data.get("active", True),
            custom_fields={"altegio_data": data}
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
            params["service_ids[]"] = service_id

        data = await self._request(
            "GET",
            f"/company/{self.company_id}/staff",
            params=params
        )

        employees = []
        for item in data if isinstance(data, list) else [data]:
            if active_only and item.get("fired"):
                continue
            if active_only and not item.get("bookable", True):
                continue
            employees.append(self._parse_employee(item))

        logger.info("altegio_employees_fetched", count=len(employees))
        return employees

    async def get_employee_by_id(self, employee_id: str) -> Optional[CRMEmployee]:
        """Получение сотрудника по ID"""
        try:
            data = await self._request(
                "GET",
                f"/company/{self.company_id}/staff/{employee_id}"
            )
            return self._parse_employee(data)
        except Exception:
            return None

    def _parse_employee(self, data: Dict) -> CRMEmployee:
        """Парсинг данных сотрудника"""
        return CRMEmployee(
            id=str(data.get("id")),
            name=data.get("name", ""),
            specialization=data.get("specialization"),
            is_active=not data.get("fired", False) and data.get("bookable", True),
            rating=float(data.get("rating", 0)) if data.get("rating") else None,
            custom_fields={"altegio_data": data}
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
        slots = []

        # Получаем доступные даты
        params = {"service_ids[]": service_id}
        if employee_id:
            params["staff_id"] = employee_id

        dates_data = await self._request(
            "GET",
            f"/book_dates/{self.company_id}",
            params=params
        )

        # Фильтруем даты в нужном диапазоне
        available_dates = []
        for date_item in dates_data.get("booking_dates", []):
            d = datetime.strptime(date_item, "%Y-%m-%d").date()
            if start_date <= d <= end_date:
                available_dates.append(d)

        # Для каждой даты получаем доступные времена
        for slot_date in available_dates:
            if employee_id:
                staff_ids = [employee_id]
            else:
                staff_data = await self._request(
                    "GET",
                    f"/book_staff/{self.company_id}",
                    params={
                        "service_ids[]": service_id,
                        "datetime": slot_date.strftime("%Y-%m-%d")
                    }
                )
                staff_ids = [str(s.get("id")) for s in staff_data if isinstance(staff_data, list)]
                if not staff_ids:
                    continue

            for staff_id in staff_ids:
                times_data = await self._request(
                    "GET",
                    f"/book_times/{self.company_id}/{staff_id}/{slot_date.strftime('%Y-%m-%d')}",
                    params={"service_ids[]": service_id}
                )

                for time_item in times_data if isinstance(times_data, list) else []:
                    if time_item.get("disabled"):
                        continue

                    slot_time = datetime.strptime(time_item.get("time", "00:00"), "%H:%M").time()

                    slots.append(CRMTimeSlot(
                        slot_date=slot_date,
                        slot_time=slot_time,
                        duration_minutes=time_item.get("duration", 60) // 60,
                        employee_id=staff_id,
                        service_id=service_id,
                        is_available=True
                    ))

        logger.info("altegio_slots_fetched", count=len(slots))
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

        # Получаем данные клиента если есть ID
        phone = ""
        fullname = ""
        email = ""

        if appointment.client_id:
            try:
                client_data = await self._request(
                    "GET",
                    f"/company/{self.company_id}/client/{appointment.client_id}"
                )
                phone = client_data.get("phone", "")
                fullname = client_data.get("name", "")
                email = client_data.get("email", "")
            except Exception:
                pass

        payload = {
            "phone": phone,
            "fullname": fullname,
            "email": email,
            "appointments": [{
                "id": 1,
                "services": [int(appointment.service_id)],
                "staff_id": int(appointment.employee_id) if appointment.employee_id else 0,
                "datetime": appointment_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
            }],
            "comment": appointment.notes or ""
        }

        data = await self._request(
            "POST",
            f"/book_record/{self.company_id}",
            json=payload
        )

        record_id = str(data[0].get("id")) if isinstance(data, list) else str(data.get("id"))

        logger.info("altegio_appointment_created", record_id=record_id)

        return CRMAppointment(
            id=record_id,
            client_id=appointment.client_id,
            service_id=appointment.service_id,
            employee_id=appointment.employee_id,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            duration_minutes=appointment.duration_minutes,
            status="confirmed",
            notes=appointment.notes,
            custom_fields={"altegio_data": data}
        )

    async def get_appointment_by_id(self, appointment_id: str) -> Optional[CRMAppointment]:
        """Получение записи по ID"""
        try:
            data = await self._request(
                "GET",
                f"/record/{self.company_id}/{appointment_id}"
            )
            return self._parse_appointment(data)
        except Exception:
            return None

    async def cancel_appointment(self, appointment_id: str) -> bool:
        """Отмена записи"""
        try:
            await self._request(
                "DELETE",
                f"/record/{self.company_id}/{appointment_id}"
            )
            logger.info("altegio_appointment_cancelled", appointment_id=appointment_id)
            return True
        except Exception as e:
            logger.error("altegio_cancel_failed", error=str(e))
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
            f"/records/{self.company_id}",
            params=params
        )

        return [self._parse_appointment(item) for item in data if isinstance(data, list)]

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

        services = data.get("services", [])
        service_id = str(services[0].get("id")) if services else ""

        status_map = {0: "pending", 1: "confirmed", 2: "completed", -1: "cancelled"}
        status = status_map.get(data.get("attendance", 0), "confirmed")

        return CRMAppointment(
            id=str(data.get("id")),
            client_id=str(data.get("client", {}).get("id", "")),
            service_id=service_id,
            employee_id=str(data.get("staff", {}).get("id", "")),
            appointment_date=appt_date,
            appointment_time=appt_time,
            duration_minutes=data.get("length", 60),
            status=status,
            notes=data.get("comment"),
            custom_fields={"altegio_data": data}
        )

    # ============================================
    # WEBHOOKS (уникально для Altegio)
    # ============================================

    async def setup_webhook(self, url: str, events: List[str]) -> Dict[str, Any]:
        """
        Настройка webhook для получения событий

        Args:
            url: URL для получения webhook
            events: Список событий (record_created, record_updated, record_deleted и т.д.)

        Returns:
            Данные созданного webhook
        """
        payload = {
            "url": url,
            "events": events
        }

        data = await self._request(
            "POST",
            f"/company/{self.company_id}/webhooks",
            json=payload
        )

        logger.info("altegio_webhook_created", webhook_url=url)
        return data

    async def delete_webhook(self, webhook_id: str) -> bool:
        """Удаление webhook"""
        try:
            await self._request(
                "DELETE",
                f"/company/{self.company_id}/webhooks/{webhook_id}"
            )
            return True
        except Exception:
            return False

    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================

    async def health_check(self) -> bool:
        """Проверка доступности Altegio API"""
        try:
            await self._request("GET", f"/company/{self.company_id}")
            return True
        except Exception as e:
            logger.error("altegio_health_check_failed", error=str(e))
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

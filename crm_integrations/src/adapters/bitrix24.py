"""
Битрикс24 CRM Adapter

Документация API: https://apidocs.bitrix24.com/
Webhooks: https://helpdesk.bitrix24.com/courses/index.php?COURSE_ID=268&LESSON_ID=26002

URL формат: https://{domain}.bitrix24.ru/rest/{user_id}/{webhook_secret}/{method}

Особенности:
- Webhooks не требуют OAuth 2.0
- Rate limit зависит от тарифа (обычно 2 запроса/сек)
- Max 50 записей на запрос (для list методов)
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

# Rate limiter - max 2 requests per second (conservative)
_last_request_time = 0
_request_interval = 0.5  # 500ms between requests


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


class Bitrix24Adapter(BaseCRMAdapter):
    """
    Адаптер для Битрикс24 CRM

    Битрикс24 - комплексная CRM для малого и среднего бизнеса.
    #1 CRM система в России по количеству пользователей.

    Требует:
        - api_key: Webhook URL или секретный ключ webhook
        - base_url: URL вашего Битрикс24 портала (например, https://your-company.bitrix24.ru)

    Формат webhook URL:
        https://your-company.bitrix24.ru/rest/{user_id}/{webhook_secret}/
    """

    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        """
        Args:
            api_key: Webhook URL или секретный ключ
            base_url: Базовый URL Битрикс24 портала
        """
        super().__init__(api_key, base_url, **kwargs)

        # Определяем REST URL
        if api_key.startswith("http"):
            # api_key уже содержит полный URL webhook
            self.rest_url = api_key.rstrip("/")
        else:
            # api_key - это секрет webhook, нужен base_url
            if not base_url:
                raise ValueError("base_url обязателен, если api_key не полный URL")
            self.rest_url = f"{base_url.rstrip('/')}/rest/1/{api_key}"

        # HTTP client
        self.client = httpx.AsyncClient(timeout=30.0)

        logger.info("bitrix24_adapter_initialized", rest_url=self.rest_url[:50] + "...")

    @rate_limit
    async def _request(
        self,
        method: str,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Выполнение запроса к Bitrix24 API

        Args:
            method: Название метода API (например, crm.contact.list)
            params: Параметры запроса

        Returns:
            Ответ API
        """
        url = f"{self.rest_url}/{method}"

        try:
            response = await self.client.post(url, json=params or {})
            response.raise_for_status()

            data = response.json()

            # Bitrix24 возвращает {"result": ..., "error": ..., "error_description": ...}
            if "error" in data:
                error_msg = data.get("error_description", data.get("error", "Unknown error"))
                logger.error("bitrix24_api_error", error=error_msg, method=method)
                raise Exception(f"Bitrix24 API error: {error_msg}")

            return data.get("result", data)

        except httpx.HTTPStatusError as e:
            logger.error(
                "bitrix24_http_error",
                status_code=e.response.status_code,
                method=method
            )
            raise
        except Exception as e:
            logger.error("bitrix24_request_error", error=str(e), method=method)
            raise

    # ============================================
    # РАБОТА С КЛИЕНТАМИ (Контакты)
    # ============================================

    async def get_client_by_phone(self, phone: str) -> Optional[CRMClient]:
        """Поиск клиента (контакта) по номеру телефона"""
        try:
            # Нормализуем телефон
            clean_phone = ''.join(filter(str.isdigit, phone))

            # Поиск по телефону
            data = await self._request(
                "crm.contact.list",
                {
                    "filter": {"PHONE": clean_phone},
                    "select": ["ID", "NAME", "LAST_NAME", "EMAIL", "PHONE", "COMMENTS"]
                }
            )

            if not data:
                return None

            # Берем первого найденного
            contact = data[0] if isinstance(data, list) else data

            return self._parse_client(contact)

        except Exception as e:
            logger.warning("bitrix24_client_search_failed", phone=phone[-4:], error=str(e))
            return None

    async def create_client(self, client: CRMClient) -> CRMClient:
        """Создание нового контакта"""
        # Разбиваем имя на части
        name_parts = (client.name or "").split() if client.name else []
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        fields = {
            "NAME": first_name,
            "LAST_NAME": last_name,
            "PHONE": [{"VALUE": client.phone, "VALUE_TYPE": "MOBILE"}],
            "COMMENTS": client.notes or ""
        }

        if client.email:
            fields["EMAIL"] = [{"VALUE": client.email, "VALUE_TYPE": "WORK"}]

        data = await self._request("crm.contact.add", {"fields": fields})

        # data содержит ID нового контакта
        contact_id = str(data) if isinstance(data, int) else str(data.get("ID", data))

        logger.info("bitrix24_client_created", client_id=contact_id)

        return CRMClient(
            id=contact_id,
            phone=client.phone,
            name=client.name,
            email=client.email,
            notes=client.notes,
            custom_fields={"bitrix24_id": contact_id}
        )

    async def update_client(self, client: CRMClient) -> CRMClient:
        """Обновление данных контакта"""
        if not client.id:
            raise ValueError("Client ID is required for update")

        name_parts = (client.name or "").split() if client.name else []
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        fields = {
            "NAME": first_name,
            "LAST_NAME": last_name,
            "COMMENTS": client.notes or ""
        }

        if client.phone:
            fields["PHONE"] = [{"VALUE": client.phone, "VALUE_TYPE": "MOBILE"}]

        if client.email:
            fields["EMAIL"] = [{"VALUE": client.email, "VALUE_TYPE": "WORK"}]

        await self._request("crm.contact.update", {"id": client.id, "fields": fields})

        logger.info("bitrix24_client_updated", client_id=client.id)
        return client

    def _parse_client(self, data: Dict) -> CRMClient:
        """Парсинг данных контакта"""
        # Собираем имя
        first_name = data.get("NAME", "")
        last_name = data.get("LAST_NAME", "")
        full_name = f"{first_name} {last_name}".strip()

        # Телефон - массив объектов
        phones = data.get("PHONE", [])
        phone = phones[0].get("VALUE", "") if phones else ""

        # Email - массив объектов
        emails = data.get("EMAIL", [])
        email = emails[0].get("VALUE", "") if emails else ""

        return CRMClient(
            id=str(data.get("ID")),
            phone=phone,
            name=full_name if full_name else None,
            email=email if email else None,
            notes=data.get("COMMENTS"),
            custom_fields={"bitrix24_data": data}
        )

    # ============================================
    # РАБОТА С УСЛУГАМИ (Товары/Услуги)
    # ============================================

    async def get_services(
        self,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[CRMService]:
        """
        Получение списка услуг/товаров

        В Битрикс24 услуги хранятся как товары (crm.product.*)
        """
        params = {
            "select": ["ID", "NAME", "DESCRIPTION", "PRICE", "SECTION_ID", "ACTIVE"],
            "order": {"NAME": "ASC"}
        }

        if category:
            params["filter"] = {"SECTION_ID": category}

        if active_only:
            params.setdefault("filter", {})["ACTIVE"] = "Y"

        data = await self._request("crm.product.list", params)

        services = []
        for item in data if isinstance(data, list) else []:
            services.append(self._parse_service(item))

        logger.info("bitrix24_services_fetched", count=len(services))
        return services

    async def get_service_by_id(self, service_id: str) -> Optional[CRMService]:
        """Получение услуги/товара по ID"""
        try:
            data = await self._request("crm.product.get", {"id": service_id})
            return self._parse_service(data)
        except Exception:
            return None

    def _parse_service(self, data: Dict) -> CRMService:
        """Парсинг данных услуги/товара"""
        return CRMService(
            id=str(data.get("ID")),
            title=data.get("NAME", ""),
            description=data.get("DESCRIPTION", ""),
            price=float(data.get("PRICE", 0)),
            category=data.get("SECTION_ID"),
            is_active=data.get("ACTIVE") == "Y",
            custom_fields={"bitrix24_data": data}
        )

    # ============================================
    # РАБОТА С СОТРУДНИКАМИ
    # ============================================

    async def get_employees(
        self,
        service_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[CRMEmployee]:
        """
        Получение списка сотрудников

        В Битрикс24 сотрудники - это пользователи (user.*)
        """
        params = {
            "select": ["ID", "NAME", "LAST_NAME", "WORK_POSITION", "ACTIVE"],
        }

        if active_only:
            params["filter"] = {"ACTIVE": True}

        data = await self._request("user.get", params)

        employees = []
        for item in data if isinstance(data, list) else []:
            employees.append(self._parse_employee(item))

        logger.info("bitrix24_employees_fetched", count=len(employees))
        return employees

    async def get_employee_by_id(self, employee_id: str) -> Optional[CRMEmployee]:
        """Получение сотрудника по ID"""
        try:
            data = await self._request("user.get", {"ID": employee_id})
            if data:
                return self._parse_employee(data[0] if isinstance(data, list) else data)
            return None
        except Exception:
            return None

    def _parse_employee(self, data: Dict) -> CRMEmployee:
        """Парсинг данных сотрудника"""
        first_name = data.get("NAME", "")
        last_name = data.get("LAST_NAME", "")
        full_name = f"{first_name} {last_name}".strip()

        return CRMEmployee(
            id=str(data.get("ID")),
            name=full_name,
            specialization=data.get("WORK_POSITION"),
            is_active=data.get("ACTIVE", True),
            custom_fields={"bitrix24_data": data}
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
        """
        Получение доступных слотов

        Битрикс24 использует календари для управления расписанием.
        Слоты формируются на основе событий календаря и рабочего времени.
        """
        # Получаем события календаря
        params = {
            "type": "company_calendar",
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
        }

        if employee_id:
            params["ownerId"] = employee_id

        try:
            data = await self._request("calendar.event.get", params)
        except Exception as e:
            logger.warning("bitrix24_calendar_error", error=str(e))
            data = []

        # Собираем занятые слоты
        busy_slots = set()
        for event in data if isinstance(data, list) else []:
            event_start = event.get("DATE_FROM", "")
            if event_start:
                busy_slots.add(event_start[:16])  # YYYY-MM-DDTHH:MM

        # Генерируем доступные слоты (9:00 - 18:00, каждые 30 мин)
        slots = []
        current_date = start_date
        while current_date <= end_date:
            for hour in range(9, 18):  # 9:00 - 17:30
                for minute in [0, 30]:
                    slot_datetime = datetime.combine(
                        current_date,
                        time(hour, minute)
                    )
                    slot_key = slot_datetime.strftime("%Y-%m-%dT%H:%M")

                    if slot_key not in busy_slots:
                        slots.append(CRMTimeSlot(
                            slot_date=current_date,
                            slot_time=time(hour, minute),
                            duration_minutes=30,
                            employee_id=employee_id,
                            service_id=service_id,
                            is_available=True
                        ))

            current_date = date(
                current_date.year,
                current_date.month,
                current_date.day + 1
            ) if current_date.day < 28 else date(
                current_date.year if current_date.month < 12 else current_date.year + 1,
                current_date.month + 1 if current_date.month < 12 else 1,
                1
            )

        logger.info("bitrix24_slots_generated", count=len(slots))
        return slots[:100]  # Ограничиваем количество

    # ============================================
    # РАБОТА С ЗАПИСЯМИ (Сделки + События)
    # ============================================

    async def create_appointment(self, appointment: CRMAppointment) -> CRMAppointment:
        """
        Создание записи

        В Битрикс24 запись = Сделка + Событие календаря
        """
        # 1. Создаем сделку
        deal_fields = {
            "TITLE": f"Запись на услугу #{appointment.service_id}",
            "CONTACT_ID": appointment.client_id,
            "COMMENTS": appointment.notes or "",
            "STAGE_ID": "NEW",  # Новая сделка
        }

        deal_id = await self._request("crm.deal.add", {"fields": deal_fields})

        # 2. Создаем событие в календаре
        appointment_datetime = datetime.combine(
            appointment.appointment_date,
            appointment.appointment_time
        )
        end_datetime = datetime.combine(
            appointment.appointment_date,
            time(
                appointment.appointment_time.hour,
                appointment.appointment_time.minute + appointment.duration_minutes
            )
        )

        event_fields = {
            "name": f"Запись клиента (Сделка #{deal_id})",
            "dateFrom": appointment_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
            "dateTo": end_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
            "description": appointment.notes or "",
        }

        if appointment.employee_id:
            event_fields["ownerId"] = appointment.employee_id

        try:
            await self._request("calendar.event.add", event_fields)
        except Exception as e:
            logger.warning("bitrix24_calendar_event_failed", error=str(e))

        record_id = str(deal_id) if isinstance(deal_id, int) else str(deal_id.get("ID", deal_id))

        logger.info("bitrix24_appointment_created", deal_id=record_id)

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
            custom_fields={"bitrix24_deal_id": record_id}
        )

    async def get_appointment_by_id(self, appointment_id: str) -> Optional[CRMAppointment]:
        """Получение записи (сделки) по ID"""
        try:
            data = await self._request("crm.deal.get", {"id": appointment_id})
            return self._parse_appointment(data)
        except Exception:
            return None

    async def cancel_appointment(self, appointment_id: str) -> bool:
        """Отмена записи (перевод сделки в статус Отменена)"""
        try:
            await self._request(
                "crm.deal.update",
                {
                    "id": appointment_id,
                    "fields": {"STAGE_ID": "LOSE"}  # Проигранная/отмененная
                }
            )
            logger.info("bitrix24_appointment_cancelled", deal_id=appointment_id)
            return True
        except Exception as e:
            logger.error("bitrix24_cancel_failed", error=str(e))
            return False

    async def get_client_appointments(
        self,
        client_id: str,
        include_past: bool = False
    ) -> List[CRMAppointment]:
        """Получение записей (сделок) клиента"""
        params = {
            "filter": {"CONTACT_ID": client_id},
            "select": ["ID", "TITLE", "STAGE_ID", "DATE_CREATE", "COMMENTS", "CONTACT_ID"]
        }

        if not include_past:
            params["filter"]["STAGE_ID"] = ["NEW", "PREPARATION", "PREPAYMENT_INVOICE"]

        data = await self._request("crm.deal.list", params)

        return [self._parse_appointment(item) for item in data if isinstance(data, list)]

    def _parse_appointment(self, data: Dict) -> CRMAppointment:
        """Парсинг данных сделки как записи"""
        # Парсим дату создания как дату записи (упрощение)
        date_str = data.get("DATE_CREATE", "")
        if date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00").replace("+03:00", ""))
            appt_date = dt.date()
            appt_time = dt.time()
        else:
            appt_date = date.today()
            appt_time = time(0, 0)

        # Маппинг статусов
        stage = data.get("STAGE_ID", "")
        status_map = {
            "NEW": "pending",
            "PREPARATION": "confirmed",
            "PREPAYMENT_INVOICE": "confirmed",
            "EXECUTING": "in_progress",
            "WON": "completed",
            "LOSE": "cancelled"
        }
        status = status_map.get(stage, "confirmed")

        return CRMAppointment(
            id=str(data.get("ID")),
            client_id=str(data.get("CONTACT_ID", "")),
            service_id="",  # Не хранится в стандартных полях сделки
            employee_id=str(data.get("ASSIGNED_BY_ID", "")),
            appointment_date=appt_date,
            appointment_time=appt_time,
            duration_minutes=60,  # По умолчанию
            status=status,
            notes=data.get("COMMENTS"),
            custom_fields={"bitrix24_data": data}
        )

    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================

    async def health_check(self) -> bool:
        """Проверка доступности Битрикс24 API"""
        try:
            # Простой запрос для проверки
            await self._request("app.info")
            return True
        except Exception as e:
            logger.error("bitrix24_health_check_failed", error=str(e))
            return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

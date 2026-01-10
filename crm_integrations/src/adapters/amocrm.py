"""
amoCRM Adapter

amoCRM - популярная CRM система для малого и среднего бизнеса в России.
Особенно популярна для отделов продаж, но также используется в сфере услуг.

Документация API:
- Официальная: https://developers.amocrm.com/rest_api/
- API v4: https://www.amocrm.ru/developers/content/crm_platform/api-reference

Особенности:
- REST API v4 (текущая версия)
- OAuth 2.0 авторизация (с июня 2020 - обязательно)
- Refresh tokens одноразовые (обновляются при каждом запросе access token)
- Rate limit: зависит от тарифа

URL формат: https://{subdomain}.amocrm.ru/api/v4/{resource}

Важно для сферы услуг:
- amoCRM ориентирована на продажи (лиды, сделки)
- Для записей клиентов используются сделки (deals) + задачи (tasks)
- Нет встроенного календаря слотов как в YCLIENTS
- Рекомендуется для компаний, которым важна воронка продаж
"""

import httpx
import asyncio
from typing import List, Optional, Dict, Any
from datetime import date, time, datetime, timedelta
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


class AmoCRMAdapter(BaseCRMAdapter):
    """
    Адаптер для amoCRM

    amoCRM - CRM для продаж, популярная в России для малого и среднего бизнеса.

    ВАЖНО: amoCRM ориентирована на продажи, а не на запись клиентов.
    Для сферы услуг (салоны, фитнес) лучше использовать YCLIENTS или Altegio.
    Однако если компания уже использует amoCRM, этот адаптер позволит интеграцию.

    Требует:
        - api_key: Access Token (OAuth 2.0)
        - base_url: URL вашего аккаунта (https://your-subdomain.amocrm.ru)
        - refresh_token: Refresh Token для обновления Access Token

    Особенности реализации:
        - Клиенты = Контакты (contacts)
        - Услуги = Товары в каталоге (catalogs) или custom fields
        - Записи = Сделки (leads) + Задачи (tasks)
        - Сотрудники = Пользователи (users)
    """

    API_VERSION = "v4"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        **kwargs
    ):
        """
        Args:
            api_key: Access Token (OAuth 2.0)
            base_url: URL аккаунта amoCRM (например: https://company.amocrm.ru)
            refresh_token: Refresh Token для обновления access token
            client_id: ID интеграции (для OAuth)
            client_secret: Secret интеграции (для OAuth)
        """
        super().__init__(api_key, base_url, **kwargs)

        self.access_token = api_key
        self.refresh_token = refresh_token
        self.client_id = client_id or kwargs.get('client_id')
        self.client_secret = client_secret or kwargs.get('client_secret')

        # API URL
        if base_url:
            self.api_url = f"{base_url.rstrip('/')}/api/{self.API_VERSION}"
        else:
            raise ValueError("base_url обязателен для amoCRM")

        # HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=30.0,
            headers=self._get_headers()
        )

        logger.info(
            "amocrm_adapter_initialized",
            base_url=self.base_url[:30] + "..." if self.base_url else None
        )

    def _get_headers(self) -> Dict[str, str]:
        """Формирование заголовков"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _refresh_access_token(self) -> bool:
        """
        Обновление access token через refresh token

        ВАЖНО: amoCRM возвращает новый refresh_token при каждом обновлении.
        Старый refresh_token становится недействительным.
        """
        if not all([self.refresh_token, self.client_id, self.client_secret]):
            logger.warning("amocrm_cannot_refresh_token", reason="missing credentials")
            return False

        try:
            response = await self.client.post(
                f"{self.base_url}/oauth2/access_token",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                }
            )
            response.raise_for_status()
            data = response.json()

            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]  # ВАЖНО: сохранить новый!

            # Обновляем заголовки
            self.client.headers.update(self._get_headers())

            logger.info("amocrm_token_refreshed")
            return True

        except Exception as e:
            logger.error("amocrm_token_refresh_failed", error=str(e))
            return False

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        retry_on_401: bool = True
    ) -> Dict[str, Any]:
        """Выполнение запроса к API"""
        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json
            )

            # Если 401 - пробуем обновить токен
            if response.status_code == 401 and retry_on_401:
                if await self._refresh_access_token():
                    return await self._request(
                        method, endpoint, params, json, retry_on_401=False
                    )

            response.raise_for_status()

            if response.status_code == 204:
                return {}

            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "amocrm_http_error",
                status_code=e.response.status_code,
                endpoint=endpoint
            )
            raise
        except Exception as e:
            logger.error("amocrm_request_error", error=str(e), endpoint=endpoint)
            raise

    # ============================================
    # РАБОТА С КЛИЕНТАМИ (Контакты)
    # ============================================

    async def get_client_by_phone(self, phone: str) -> Optional[CRMClient]:
        """Поиск клиента (контакта) по номеру телефона"""
        try:
            clean_phone = ''.join(filter(str.isdigit, phone))

            # amoCRM использует query для поиска
            data = await self._request(
                "GET",
                "/contacts",
                params={"query": clean_phone}
            )

            contacts = data.get("_embedded", {}).get("contacts", [])
            if not contacts:
                return None

            return self._parse_client(contacts[0])

        except Exception as e:
            logger.warning("amocrm_client_search_failed", phone=phone[-4:], error=str(e))
            return None

    async def create_client(self, client: CRMClient) -> CRMClient:
        """Создание нового контакта"""
        # Формируем custom fields для телефона и email
        custom_fields = []

        if client.phone:
            custom_fields.append({
                "field_code": "PHONE",
                "values": [{"value": client.phone, "enum_code": "MOB"}]
            })

        if client.email:
            custom_fields.append({
                "field_code": "EMAIL",
                "values": [{"value": client.email, "enum_code": "WORK"}]
            })

        payload = [{
            "name": client.name or "Клиент",
            "custom_fields_values": custom_fields
        }]

        data = await self._request("POST", "/contacts", json=payload)

        contacts = data.get("_embedded", {}).get("contacts", [])
        if contacts:
            contact_id = str(contacts[0].get("id"))
            logger.info("amocrm_client_created", client_id=contact_id)

            return CRMClient(
                id=contact_id,
                phone=client.phone,
                name=client.name,
                email=client.email,
                notes=client.notes,
                custom_fields={"amocrm_data": contacts[0]}
            )

        raise Exception("Failed to create contact in amoCRM")

    async def update_client(self, client: CRMClient) -> CRMClient:
        """Обновление контакта"""
        if not client.id:
            raise ValueError("Client ID is required for update")

        custom_fields = []
        if client.phone:
            custom_fields.append({
                "field_code": "PHONE",
                "values": [{"value": client.phone, "enum_code": "MOB"}]
            })
        if client.email:
            custom_fields.append({
                "field_code": "EMAIL",
                "values": [{"value": client.email, "enum_code": "WORK"}]
            })

        payload = [{
            "id": int(client.id),
            "name": client.name or "Клиент",
            "custom_fields_values": custom_fields
        }]

        await self._request("PATCH", "/contacts", json=payload)
        logger.info("amocrm_client_updated", client_id=client.id)

        return client

    def _parse_client(self, data: Dict) -> CRMClient:
        """Парсинг контакта"""
        # Извлекаем телефон и email из custom_fields
        phone = ""
        email = ""

        for field in data.get("custom_fields_values", []):
            field_code = field.get("field_code", "")
            values = field.get("values", [])

            if field_code == "PHONE" and values:
                phone = values[0].get("value", "")
            elif field_code == "EMAIL" and values:
                email = values[0].get("value", "")

        return CRMClient(
            id=str(data.get("id")),
            phone=phone,
            name=data.get("name"),
            email=email if email else None,
            created_at=datetime.fromtimestamp(data.get("created_at", 0)) if data.get("created_at") else None,
            custom_fields={"amocrm_data": data}
        )

    # ============================================
    # РАБОТА С УСЛУГАМИ (Каталоги/Products)
    # ============================================

    async def get_services(
        self,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[CRMService]:
        """
        Получение услуг

        В amoCRM услуги хранятся в каталогах (catalogs).
        Необходимо предварительно создать каталог "Услуги".
        """
        try:
            # Получаем список каталогов
            catalogs_data = await self._request("GET", "/catalogs")
            catalogs = catalogs_data.get("_embedded", {}).get("catalogs", [])

            # Ищем каталог услуг
            services_catalog = None
            for cat in catalogs:
                if cat.get("name", "").lower() in ["услуги", "services", "товары"]:
                    services_catalog = cat
                    break

            if not services_catalog:
                logger.warning("amocrm_services_catalog_not_found")
                return []

            # Получаем элементы каталога
            catalog_id = services_catalog.get("id")
            elements_data = await self._request(
                "GET",
                f"/catalogs/{catalog_id}/elements"
            )

            elements = elements_data.get("_embedded", {}).get("elements", [])

            services = []
            for elem in elements:
                services.append(self._parse_service(elem))

            logger.info("amocrm_services_fetched", count=len(services))
            return services

        except Exception as e:
            logger.warning("amocrm_get_services_failed", error=str(e))
            return []

    async def get_service_by_id(self, service_id: str) -> Optional[CRMService]:
        """Получение услуги по ID"""
        try:
            # Нужен catalog_id для запроса
            # Упрощаем: получаем все услуги и ищем по ID
            services = await self.get_services()
            for service in services:
                if service.id == service_id:
                    return service
            return None
        except Exception:
            return None

    def _parse_service(self, data: Dict) -> CRMService:
        """Парсинг элемента каталога как услуги"""
        # Извлекаем цену из custom fields
        price = 0
        for field in data.get("custom_fields_values", []):
            if field.get("field_code") == "PRICE":
                values = field.get("values", [])
                if values:
                    price = float(values[0].get("value", 0))

        return CRMService(
            id=str(data.get("id")),
            title=data.get("name", ""),
            description="",
            price=price,
            is_active=True,
            custom_fields={"amocrm_data": data}
        )

    # ============================================
    # РАБОТА С СОТРУДНИКАМИ (Users)
    # ============================================

    async def get_employees(
        self,
        service_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[CRMEmployee]:
        """Получение сотрудников (пользователей)"""
        try:
            data = await self._request("GET", "/users")
            users = data.get("_embedded", {}).get("users", [])

            employees = []
            for user in users:
                if active_only and not user.get("is_active", True):
                    continue
                employees.append(self._parse_employee(user))

            logger.info("amocrm_employees_fetched", count=len(employees))
            return employees

        except Exception as e:
            logger.warning("amocrm_get_employees_failed", error=str(e))
            return []

    async def get_employee_by_id(self, employee_id: str) -> Optional[CRMEmployee]:
        """Получение сотрудника по ID"""
        try:
            data = await self._request("GET", f"/users/{employee_id}")
            return self._parse_employee(data)
        except Exception:
            return None

    def _parse_employee(self, data: Dict) -> CRMEmployee:
        """Парсинг пользователя как сотрудника"""
        return CRMEmployee(
            id=str(data.get("id")),
            name=data.get("name", ""),
            specialization=data.get("role"),  # Роль как специализация
            is_active=data.get("is_active", True),
            custom_fields={"amocrm_data": data}
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

        ВАЖНО: amoCRM не имеет встроенного модуля расписания.
        Слоты генерируются на основе рабочих часов (по умолчанию 9:00-18:00).
        Занятые слоты определяются по задачам (tasks).
        """
        slots = []

        # Получаем задачи в указанный период (занятые слоты)
        try:
            tasks_data = await self._request(
                "GET",
                "/tasks",
                params={
                    "filter[complete_till][from]": int(datetime.combine(start_date, time.min).timestamp()),
                    "filter[complete_till][to]": int(datetime.combine(end_date, time.max).timestamp()),
                }
            )
            tasks = tasks_data.get("_embedded", {}).get("tasks", [])
        except Exception:
            tasks = []

        # Собираем занятые слоты
        busy_slots = set()
        for task in tasks:
            if employee_id and str(task.get("responsible_user_id")) != employee_id:
                continue
            complete_till = task.get("complete_till")
            if complete_till:
                dt = datetime.fromtimestamp(complete_till)
                busy_slots.add(dt.strftime("%Y-%m-%d %H:%M"))

        # Генерируем слоты (9:00-18:00, каждые 30 минут)
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Пн-Пт
                for hour in range(9, 18):
                    for minute in [0, 30]:
                        slot_dt = datetime.combine(current_date, time(hour, minute))
                        slot_key = slot_dt.strftime("%Y-%m-%d %H:%M")

                        if slot_key not in busy_slots:
                            slots.append(CRMTimeSlot(
                                slot_date=current_date,
                                slot_time=time(hour, minute),
                                duration_minutes=30,
                                employee_id=employee_id,
                                service_id=service_id,
                                is_available=True
                            ))

            current_date += timedelta(days=1)

        logger.info("amocrm_slots_generated", count=len(slots))
        return slots[:100]

    # ============================================
    # РАБОТА С ЗАПИСЯМИ (Сделки + Задачи)
    # ============================================

    async def create_appointment(self, appointment: CRMAppointment) -> CRMAppointment:
        """
        Создание записи

        В amoCRM запись = Сделка (lead) + Задача (task) на время записи
        """
        appointment_datetime = datetime.combine(
            appointment.appointment_date,
            appointment.appointment_time
        )

        # 1. Создаем сделку
        lead_payload = [{
            "name": f"Запись на услугу (ID: {appointment.service_id})",
            "status_id": 142,  # ID статуса "Новая" (может отличаться)
            "_embedded": {
                "contacts": [{"id": int(appointment.client_id)}]
            }
        }]

        lead_data = await self._request("POST", "/leads", json=lead_payload)
        leads = lead_data.get("_embedded", {}).get("leads", [])

        if not leads:
            raise Exception("Failed to create lead in amoCRM")

        lead_id = leads[0].get("id")

        # 2. Создаем задачу на время записи
        task_payload = [{
            "text": f"Запись клиента. {appointment.notes or ''}",
            "complete_till": int(appointment_datetime.timestamp()),
            "entity_id": lead_id,
            "entity_type": "leads",
            "responsible_user_id": int(appointment.employee_id) if appointment.employee_id else None,
            "task_type_id": 1  # Звонок (можно изменить)
        }]

        try:
            await self._request("POST", "/tasks", json=task_payload)
        except Exception as e:
            logger.warning("amocrm_task_creation_failed", error=str(e))

        logger.info("amocrm_appointment_created", lead_id=lead_id)

        return CRMAppointment(
            id=str(lead_id),
            client_id=appointment.client_id,
            service_id=appointment.service_id,
            employee_id=appointment.employee_id,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            duration_minutes=appointment.duration_minutes,
            status="confirmed",
            notes=appointment.notes,
            custom_fields={"amocrm_lead_id": lead_id}
        )

    async def get_appointment_by_id(self, appointment_id: str) -> Optional[CRMAppointment]:
        """Получение записи (сделки) по ID"""
        try:
            data = await self._request("GET", f"/leads/{appointment_id}")
            return self._parse_appointment(data)
        except Exception:
            return None

    async def cancel_appointment(self, appointment_id: str) -> bool:
        """Отмена записи (закрытие сделки как проигранной)"""
        try:
            # Переводим сделку в статус "Закрыто и не реализовано"
            payload = [{
                "id": int(appointment_id),
                "status_id": 143  # ID статуса "Закрыто" (может отличаться)
            }]

            await self._request("PATCH", "/leads", json=payload)
            logger.info("amocrm_appointment_cancelled", lead_id=appointment_id)
            return True

        except Exception as e:
            logger.error("amocrm_cancel_failed", error=str(e))
            return False

    async def get_client_appointments(
        self,
        client_id: str,
        include_past: bool = False
    ) -> List[CRMAppointment]:
        """Получение записей (сделок) клиента"""
        try:
            # Получаем сделки с фильтром по контакту
            params = {
                "filter[contacts][0][id]": client_id
            }

            data = await self._request("GET", "/leads", params=params)
            leads = data.get("_embedded", {}).get("leads", [])

            appointments = []
            for lead in leads:
                # Фильтруем по статусу если нужно
                if not include_past and lead.get("status_id") == 143:  # Закрытые
                    continue
                appointments.append(self._parse_appointment(lead))

            return appointments

        except Exception as e:
            logger.warning("amocrm_get_appointments_failed", error=str(e))
            return []

    def _parse_appointment(self, data: Dict) -> CRMAppointment:
        """Парсинг сделки как записи"""
        created_at = data.get("created_at", 0)
        dt = datetime.fromtimestamp(created_at) if created_at else datetime.now()

        # Маппинг статусов amoCRM
        status_id = data.get("status_id", 0)
        if status_id == 142:
            status = "confirmed"
        elif status_id == 143:
            status = "cancelled"
        else:
            status = "pending"

        return CRMAppointment(
            id=str(data.get("id")),
            client_id="",  # Нужен дополнительный запрос для получения
            service_id="",
            employee_id=str(data.get("responsible_user_id", "")),
            appointment_date=dt.date(),
            appointment_time=dt.time(),
            duration_minutes=60,
            status=status,
            notes=data.get("name"),
            custom_fields={"amocrm_data": data}
        )

    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================

    async def health_check(self) -> bool:
        """Проверка доступности amoCRM API"""
        try:
            await self._request("GET", "/account")
            return True
        except Exception as e:
            logger.error("amocrm_health_check_failed", error=str(e))
            return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

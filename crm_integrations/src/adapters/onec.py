"""
1C:Предприятие CRM Adapter

Документация:
- Официальная: https://its.1c.ru/db/intgr83/content/47/hdoc
- REST интерфейс: https://v8.1c.ru/platforma/rest-interfeys/
- OData 3.0: https://1c-dn.com/1c_enterprise/rest_interface/

Требования:
- 1С:Предприятие версии не ниже 8.3.5
- Веб-сервер (IIS или Apache 2.2/2.4)
- Опубликованный OData интерфейс информационной базы

URL формат: http://{server}/{base_name}/odata/standard.odata/{resource}

Особенности:
- Протокол OData 3.0
- Поддержка форматов: JSON и Atom/XML
- HTTP методы: GET (чтение), POST (создание), PATCH/PUT (обновление), DELETE (удаление)
- Доступ к справочникам (Catalog_*), документам (Document_*), регистрам (InformationRegister_*)
"""

import httpx
from typing import List, Optional, Dict, Any
from datetime import date, time, datetime
from base64 import b64encode
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


class OneCAdapter(BaseCRMAdapter):
    """
    Адаптер для 1C:Предприятие CRM

    1C:Предприятие - доминирующая система учета и CRM в корпоративном сегменте РФ.
    Использует протокол OData 3.0 для REST API.

    Требует:
        - api_key: Логин:Пароль в формате base64 или "login:password"
        - base_url: URL опубликованной информационной базы
                    (например: http://server/BaseName/odata/standard.odata)

    Важно:
        - Требуется предварительная публикация OData интерфейса на стороне 1C
        - Названия сущностей зависят от конфигурации 1C (1C:УНФ, 1C:Салон красоты и т.д.)
        - Этот адаптер использует типичные названия сущностей, которые могут
          отличаться в вашей конфигурации

    Конфигурации 1C для сферы услуг:
        - 1C:Управление нашей фирмой (УНФ) - малый бизнес
        - 1C:Салон красоты - специализированная для beauty-сегмента
        - 1C:Фитнес клуб - для фитнес-центров
        - 1C:Медицина - для медицинских центров
    """

    # Типичные имена сущностей для разных конфигураций
    # Могут быть переопределены через kwargs
    DEFAULT_ENTITY_NAMES = {
        # Справочники
        "clients": "Catalog_Контрагенты",         # или Catalog_Клиенты
        "employees": "Catalog_Сотрудники",        # или Catalog_ФизическиеЛица
        "services": "Catalog_Номенклатура",       # услуги как номенклатура

        # Документы
        "appointments": "Document_ЗаписьКлиента", # или Document_ЗаказКлиента

        # Регистры
        "schedule": "InformationRegister_РасписаниеСотрудников",
    }

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        entity_names: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        Args:
            api_key: Логин:Пароль (plain text или base64)
            base_url: URL OData сервиса 1C
            entity_names: Словарь с именами сущностей для конкретной конфигурации
        """
        super().__init__(api_key, base_url, **kwargs)

        # Определяем имена сущностей
        self.entity_names = {**self.DEFAULT_ENTITY_NAMES}
        if entity_names:
            self.entity_names.update(entity_names)

        # Конфигурация из kwargs
        if "entity_names" in kwargs:
            self.entity_names.update(kwargs["entity_names"])

        # Формируем заголовок авторизации
        if ":" in api_key and not api_key.startswith("Basic "):
            # Plain text login:password
            auth_bytes = api_key.encode('utf-8')
            auth_b64 = b64encode(auth_bytes).decode('utf-8')
            self.auth_header = f"Basic {auth_b64}"
        elif api_key.startswith("Basic "):
            self.auth_header = api_key
        else:
            # Предполагаем, что уже base64
            self.auth_header = f"Basic {api_key}"

        # HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url.rstrip("/") if self.base_url else "",
            timeout=30.0,
            headers={
                "Authorization": self.auth_header,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        logger.info(
            "onec_adapter_initialized",
            base_url=self.base_url[:50] + "..." if self.base_url else None,
            entity_names=list(self.entity_names.keys())
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Выполнение запроса к OData API 1C

        Args:
            method: HTTP метод (GET, POST, PATCH, DELETE)
            endpoint: Путь к ресурсу (например: Catalog_Контрагенты)
            params: Query параметры (OData filters, select, etc.)
            json: JSON тело запроса

        Returns:
            Ответ API
        """
        # Добавляем формат JSON
        if params is None:
            params = {}
        params["$format"] = "json"

        try:
            response = await self.client.request(
                method=method,
                url=f"/{endpoint}",
                params=params,
                json=json
            )
            response.raise_for_status()

            # Пустой ответ для DELETE
            if response.status_code == 204 or not response.content:
                return {}

            data = response.json()

            # OData возвращает {"value": [...]} для коллекций
            if isinstance(data, dict) and "value" in data:
                return data["value"]

            return data

        except httpx.HTTPStatusError as e:
            logger.error(
                "onec_http_error",
                status_code=e.response.status_code,
                endpoint=endpoint,
                response=e.response.text[:500] if e.response.text else None
            )
            raise
        except Exception as e:
            logger.error("onec_request_error", error=str(e), endpoint=endpoint)
            raise

    def _build_filter(self, conditions: Dict[str, Any]) -> str:
        """
        Построение OData $filter строки

        Args:
            conditions: Словарь условий {поле: значение}

        Returns:
            OData filter строка
        """
        filters = []
        for key, value in conditions.items():
            if isinstance(value, str):
                filters.append(f"{key} eq '{value}'")
            elif isinstance(value, bool):
                filters.append(f"{key} eq {str(value).lower()}")
            elif value is None:
                filters.append(f"{key} eq null")
            else:
                filters.append(f"{key} eq {value}")

        return " and ".join(filters)

    # ============================================
    # РАБОТА С КЛИЕНТАМИ
    # ============================================

    async def get_client_by_phone(self, phone: str) -> Optional[CRMClient]:
        """Поиск клиента по номеру телефона"""
        try:
            clean_phone = ''.join(filter(str.isdigit, phone))

            # Поиск по полям телефона (названия могут отличаться в конфигурации)
            # Пробуем разные варианты полей
            phone_fields = ["Телефон", "КонтактнаяИнформация", "ТелефонМобильный"]

            for field in phone_fields:
                try:
                    filter_str = f"substringof('{clean_phone}', {field})"
                    data = await self._request(
                        "GET",
                        self.entity_names["clients"],
                        params={
                            "$filter": filter_str,
                            "$top": 1
                        }
                    )

                    if data and isinstance(data, list) and len(data) > 0:
                        return self._parse_client(data[0])
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.warning("onec_client_search_failed", phone=phone[-4:], error=str(e))
            return None

    async def create_client(self, client: CRMClient) -> CRMClient:
        """Создание нового клиента (контрагента)"""
        payload = {
            "Description": client.name or "",
            "Наименование": client.name or "",
            "Телефон": client.phone,
            "ЭлектроннаяПочта": client.email or "",
            "Комментарий": client.notes or "",
        }

        data = await self._request(
            "POST",
            self.entity_names["clients"],
            json=payload
        )

        client_id = data.get("Ref_Key", data.get("Ссылка", ""))
        logger.info("onec_client_created", client_id=client_id)

        return CRMClient(
            id=str(client_id),
            phone=client.phone,
            name=client.name,
            email=client.email,
            notes=client.notes,
            custom_fields={"onec_data": data}
        )

    async def update_client(self, client: CRMClient) -> CRMClient:
        """Обновление данных клиента"""
        if not client.id:
            raise ValueError("Client ID is required for update")

        payload = {
            "Description": client.name or "",
            "Наименование": client.name or "",
            "Телефон": client.phone,
            "ЭлектроннаяПочта": client.email or "",
            "Комментарий": client.notes or "",
        }

        # В OData для обновления используем ключ в URL
        await self._request(
            "PATCH",
            f"{self.entity_names['clients']}(guid'{client.id}')",
            json=payload
        )

        logger.info("onec_client_updated", client_id=client.id)
        return client

    def _parse_client(self, data: Dict) -> CRMClient:
        """Парсинг данных клиента из ответа 1C"""
        # Пробуем разные варианты полей (зависят от конфигурации)
        client_id = data.get("Ref_Key", data.get("Ссылка", data.get("Ref", "")))
        name = data.get("Description", data.get("Наименование", ""))
        phone = data.get("Телефон", data.get("ТелефонМобильный", ""))
        email = data.get("ЭлектроннаяПочта", data.get("Email", ""))
        notes = data.get("Комментарий", data.get("Comment", ""))

        return CRMClient(
            id=str(client_id),
            phone=phone,
            name=name if name else None,
            email=email if email else None,
            notes=notes if notes else None,
            custom_fields={"onec_data": data}
        )

    # ============================================
    # РАБОТА С УСЛУГАМИ
    # ============================================

    async def get_services(
        self,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[CRMService]:
        """
        Получение списка услуг (номенклатуры типа "Услуга")
        """
        params = {}

        # Фильтр по типу номенклатуры = Услуга
        filters = []
        if active_only:
            filters.append("DeletionMark eq false")

        # Фильтр по виду номенклатуры (если поле существует)
        filters.append("ВидНоменклатуры eq 'Услуга'")

        if category:
            filters.append(f"Родитель eq guid'{category}'")

        if filters:
            params["$filter"] = " and ".join(filters)

        try:
            data = await self._request(
                "GET",
                self.entity_names["services"],
                params=params
            )
        except Exception:
            # Если фильтр не работает, получаем все
            data = await self._request(
                "GET",
                self.entity_names["services"],
                params={"$filter": "DeletionMark eq false"} if active_only else None
            )

        services = []
        for item in data if isinstance(data, list) else [data]:
            services.append(self._parse_service(item))

        logger.info("onec_services_fetched", count=len(services))
        return services

    async def get_service_by_id(self, service_id: str) -> Optional[CRMService]:
        """Получение услуги по ID"""
        try:
            data = await self._request(
                "GET",
                f"{self.entity_names['services']}(guid'{service_id}')"
            )
            return self._parse_service(data)
        except Exception:
            return None

    def _parse_service(self, data: Dict) -> CRMService:
        """Парсинг данных услуги"""
        service_id = data.get("Ref_Key", data.get("Ссылка", ""))
        title = data.get("Description", data.get("Наименование", ""))
        description = data.get("Описание", data.get("ПолноеНаименование", ""))
        price = float(data.get("Цена", data.get("ЦенаПродажи", 0)) or 0)
        duration = data.get("Длительность", data.get("НормаВремени"))

        return CRMService(
            id=str(service_id),
            title=title,
            description=description if description else None,
            price=price,
            duration_minutes=int(duration) if duration else None,
            category=data.get("Родитель", {}).get("Description") if isinstance(data.get("Родитель"), dict) else None,
            is_active=not data.get("DeletionMark", False),
            custom_fields={"onec_data": data}
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

        if active_only:
            params["$filter"] = "DeletionMark eq false"

        data = await self._request(
            "GET",
            self.entity_names["employees"],
            params=params
        )

        employees = []
        for item in data if isinstance(data, list) else [data]:
            employees.append(self._parse_employee(item))

        logger.info("onec_employees_fetched", count=len(employees))
        return employees

    async def get_employee_by_id(self, employee_id: str) -> Optional[CRMEmployee]:
        """Получение сотрудника по ID"""
        try:
            data = await self._request(
                "GET",
                f"{self.entity_names['employees']}(guid'{employee_id}')"
            )
            return self._parse_employee(data)
        except Exception:
            return None

    def _parse_employee(self, data: Dict) -> CRMEmployee:
        """Парсинг данных сотрудника"""
        emp_id = data.get("Ref_Key", data.get("Ссылка", ""))
        name = data.get("Description", data.get("Наименование", data.get("ФИО", "")))
        position = data.get("Должность", data.get("Description", ""))

        return CRMEmployee(
            id=str(emp_id),
            name=name,
            specialization=position if isinstance(position, str) else None,
            is_active=not data.get("DeletionMark", False),
            custom_fields={"onec_data": data}
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

        Примечание: В 1C расписание обычно хранится в регистре сведений.
        Структура зависит от конфигурации.
        """
        slots = []

        try:
            # Пробуем получить расписание из регистра
            params = {
                "$filter": f"Период ge datetime'{start_date.isoformat()}T00:00:00' and Период le datetime'{end_date.isoformat()}T23:59:59'"
            }

            if employee_id:
                params["$filter"] += f" and Сотрудник_Key eq guid'{employee_id}'"

            data = await self._request(
                "GET",
                self.entity_names["schedule"],
                params=params
            )

            for item in data if isinstance(data, list) else [data]:
                slot_date_str = item.get("Период", item.get("Дата", ""))
                if slot_date_str:
                    slot_dt = datetime.fromisoformat(slot_date_str.replace("Z", "+00:00"))
                    slots.append(CRMTimeSlot(
                        slot_date=slot_dt.date(),
                        slot_time=slot_dt.time(),
                        duration_minutes=int(item.get("Длительность", 60)),
                        employee_id=str(item.get("Сотрудник_Key", "")),
                        service_id=service_id,
                        is_available=item.get("Свободен", True)
                    ))

        except Exception as e:
            logger.warning("onec_schedule_fetch_failed", error=str(e))
            # Генерируем слоты по умолчанию (рабочие часы 9:00-18:00)
            current_date = start_date
            while current_date <= end_date:
                # Пропускаем выходные
                if current_date.weekday() < 5:  # Пн-Пт
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
                current_date = date(
                    current_date.year,
                    current_date.month,
                    current_date.day + 1
                ) if current_date.day < 28 else date(
                    current_date.year if current_date.month < 12 else current_date.year + 1,
                    current_date.month + 1 if current_date.month < 12 else 1,
                    1
                )

        logger.info("onec_slots_generated", count=len(slots))
        return slots[:100]

    # ============================================
    # РАБОТА С ЗАПИСЯМИ
    # ============================================

    async def create_appointment(self, appointment: CRMAppointment) -> CRMAppointment:
        """
        Создание записи клиента

        В 1C запись обычно создается как документ (ЗаказКлиента, ЗаписьКлиента и т.п.)
        """
        appointment_datetime = datetime.combine(
            appointment.appointment_date,
            appointment.appointment_time
        )

        payload = {
            "Date": appointment_datetime.isoformat(),
            "Дата": appointment_datetime.isoformat(),
            "Контрагент_Key": appointment.client_id,
            "Клиент_Key": appointment.client_id,
            "Сотрудник_Key": appointment.employee_id,
            "Услуга_Key": appointment.service_id,
            "Номенклатура_Key": appointment.service_id,
            "Комментарий": appointment.notes or "",
            "Длительность": appointment.duration_minutes,
        }

        try:
            data = await self._request(
                "POST",
                self.entity_names["appointments"],
                json=payload
            )

            record_id = data.get("Ref_Key", data.get("Ссылка", ""))
            logger.info("onec_appointment_created", record_id=record_id)

            return CRMAppointment(
                id=str(record_id),
                client_id=appointment.client_id,
                service_id=appointment.service_id,
                employee_id=appointment.employee_id,
                appointment_date=appointment.appointment_date,
                appointment_time=appointment.appointment_time,
                duration_minutes=appointment.duration_minutes,
                status="confirmed",
                notes=appointment.notes,
                custom_fields={"onec_data": data}
            )
        except Exception as e:
            logger.error("onec_appointment_create_failed", error=str(e))
            raise

    async def get_appointment_by_id(self, appointment_id: str) -> Optional[CRMAppointment]:
        """Получение записи по ID"""
        try:
            data = await self._request(
                "GET",
                f"{self.entity_names['appointments']}(guid'{appointment_id}')"
            )
            return self._parse_appointment(data)
        except Exception:
            return None

    async def cancel_appointment(self, appointment_id: str) -> bool:
        """
        Отмена записи

        В 1C обычно делается через пометку на удаление или установку статуса
        """
        try:
            # Пробуем установить статус "Отменен"
            await self._request(
                "PATCH",
                f"{self.entity_names['appointments']}(guid'{appointment_id}')",
                json={"Статус": "Отменен", "DeletionMark": True}
            )

            logger.info("onec_appointment_cancelled", appointment_id=appointment_id)
            return True
        except Exception as e:
            logger.error("onec_cancel_failed", error=str(e))
            return False

    async def get_client_appointments(
        self,
        client_id: str,
        include_past: bool = False
    ) -> List[CRMAppointment]:
        """Получение записей клиента"""
        params = {
            "$filter": f"Контрагент_Key eq guid'{client_id}' or Клиент_Key eq guid'{client_id}'"
        }

        if not include_past:
            today = date.today().isoformat()
            params["$filter"] += f" and Date ge datetime'{today}T00:00:00'"

        try:
            data = await self._request(
                "GET",
                self.entity_names["appointments"],
                params=params
            )

            return [self._parse_appointment(item) for item in data if isinstance(data, list)]
        except Exception as e:
            logger.warning("onec_get_appointments_failed", error=str(e))
            return []

    def _parse_appointment(self, data: Dict) -> CRMAppointment:
        """Парсинг данных записи"""
        date_str = data.get("Date", data.get("Дата", ""))
        if date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            appt_date = dt.date()
            appt_time = dt.time()
        else:
            appt_date = date.today()
            appt_time = time(0, 0)

        # Определяем статус
        status_raw = data.get("Статус", "")
        deletion_mark = data.get("DeletionMark", False)

        if deletion_mark or status_raw == "Отменен":
            status = "cancelled"
        elif status_raw == "Выполнен":
            status = "completed"
        else:
            status = "confirmed"

        return CRMAppointment(
            id=str(data.get("Ref_Key", data.get("Ссылка", ""))),
            client_id=str(data.get("Контрагент_Key", data.get("Клиент_Key", ""))),
            service_id=str(data.get("Номенклатура_Key", data.get("Услуга_Key", ""))),
            employee_id=str(data.get("Сотрудник_Key", "")),
            appointment_date=appt_date,
            appointment_time=appt_time,
            duration_minutes=int(data.get("Длительность", 60)),
            status=status,
            notes=data.get("Комментарий"),
            custom_fields={"onec_data": data}
        )

    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================

    async def health_check(self) -> bool:
        """Проверка доступности 1C OData API"""
        try:
            # Запрос метаданных OData
            await self._request("GET", "$metadata")
            return True
        except Exception as e:
            logger.error("onec_health_check_failed", error=str(e))
            return False

    async def get_metadata(self) -> Dict[str, Any]:
        """
        Получение метаданных OData сервиса

        Полезно для определения доступных сущностей и их структуры
        """
        try:
            # Запрос к корню OData возвращает список доступных сущностей
            response = await self.client.get("/")
            return response.json()
        except Exception as e:
            logger.error("onec_metadata_failed", error=str(e))
            return {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

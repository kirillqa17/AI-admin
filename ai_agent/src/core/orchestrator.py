"""
Orchestrator - главный контроллер диалога

Управляет всей логикой взаимодействия с клиентом
"""

import uuid
from typing import Dict, Optional, List
from datetime import datetime, timezone
import structlog

from shared.models.message import Message, MessageType, Channel
from shared.models.session import Session, SessionState
from shared.database.connection import Database
from shared.services.company_service import CompanyService
from crm_integrations.src.factory import CRMFactory

from ..services.gemini_service import GeminiService
from ..services.prompt_manager import PromptManager
from ..services.tool_manager import ToolManager
from ..storage.redis_storage import RedisStorage
from ..config import settings

logger = structlog.get_logger(__name__)


class Orchestrator:
    """
    Главный оркестратор диалога

    Отвечает за:
    - Управление сессиями
    - Взаимодействие с Gemini
    - Выполнение function calls
    - Переходы между состояниями
    - Сохранение контекста
    - Multi-tenant: загрузка настроек компании из БД
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Args:
            database_url: URL подключения к PostgreSQL (опционально, берется из settings)
        """
        self.db = Database(database_url or settings.postgres_url)
        self.gemini = GeminiService()
        self.storage = RedisStorage()

        logger.info("orchestrator_initialized")
    
    async def initialize(self):
        """Инициализация всех компонентов"""
        await self.storage.connect()
        logger.info("orchestrator_ready")
    
    async def handle_message(self, message: Message) -> Dict[str, any]:
        """
        Обработка входящего сообщения (Multi-tenant)

        Args:
            message: Входящее сообщение

        Returns:
            Ответ агента
        """
        logger.info(
            "handling_message",
            message_id=message.id,
            session_id=message.session_id,
            channel=message.channel,
            from_user=message.from_user_id,
            company_id=message.company_id
        )

        try:
            # 1. MULTI-TENANT: Проверяем company_id
            if not message.company_id:
                raise ValueError("company_id required in message for multi-tenant")

            # 2. MULTI-TENANT: Загружаем настройки компании из БД
            async with self.db.session() as db_session:
                company_service = CompanyService(db_session)

                # Получаем CRM настройки
                crm_settings = await company_service.get_crm_settings(message.company_id)
                if not crm_settings:
                    raise ValueError(f"No CRM settings found for company {message.company_id}")

                # Получаем контекст компании для промптов
                company_context = await company_service.get_company_context(message.company_id)

                # Расшифровываем API ключ
                api_key = company_service.decrypt_api_key(crm_settings.api_key_encrypted)

                # 3. MULTI-TENANT: Создаем CRM адаптер для ЭТОЙ компании
                crm_adapter = CRMFactory.create(
                    crm_type=crm_settings.crm_type,
                    api_key=api_key,
                    base_url=crm_settings.base_url
                )

                # 4. MULTI-TENANT: Создаем Tool Manager и Prompt Manager для этой компании
                tool_manager = ToolManager(crm_adapter=crm_adapter)
                prompt_manager = PromptManager(company_context=company_context)

                # 5. Загружаем или создаем сессию
                session = await self._get_or_create_session(message)

                # Обновляем сессию
                session.last_activity_at = datetime.now(timezone.utc)
                session.message_ids.append(message.id)

                # Формируем контекст диалога
                conversation_history = await self._build_conversation_history(session)

                # Добавляем текущее сообщение пользователя в историю Redis
                await self.storage.add_message_to_history(
                    session_id=session.id,
                    role="user",
                    content=message.text
                )

                # Добавляем текущее сообщение в контекст для Gemini
                conversation_history.append({
                    "role": "user",
                    "parts": [{"text": message.text}]
                })

                # Получаем системный промпт
                system_prompt = prompt_manager.get_system_prompt(
                    state=session.state,
                    session_context=session.context
                )

                # Получаем инструменты для function calling
                tools = tool_manager.get_tools_for_gemini()

                # Генерируем ответ от Gemini
                response = await self.gemini.generate_response(
                    messages=conversation_history,
                    tools=tools,
                    system_instruction=system_prompt
                )

                # Обрабатываем ответ (передаем tool_manager в метод)
                result = await self._process_gemini_response(response, session, tool_manager)

                # Сохраняем ответ модели в историю (если есть текст)
                if result.get("text"):
                    await self.storage.add_message_to_history(
                        session_id=session.id,
                        role="model",
                        content=result["text"]
                    )

                # Обновляем состояние сессии на основе контекста
                await self._update_session_state(session)

                # Сохраняем сессию
                await self.storage.save_session(session)

                logger.info(
                    "message_handled_successfully",
                    session_id=session.id,
                    company_id=message.company_id,
                    new_state=session.state,
                    has_function_call=result.get("function_called", False)
                )

                return result

        except Exception as e:
            logger.error(
                "message_handling_error",
                error=str(e),
                exc_info=True
            )
            return {
                "text": "Извините, произошла ошибка. Пожалуйста, попробуйте еще раз.",
                "error": str(e)
            }
    
    async def _get_or_create_session(self, message: Message) -> Session:
        """Получить существующую или создать новую сессию"""
        session = await self.storage.get_session(message.session_id)

        if session:
            logger.debug("session_found", session_id=message.session_id)
            return session

        # Создаем новую сессию
        session = Session(
            id=message.session_id,
            user_id=message.from_user_id,
            channel=message.channel.value,
            company_id=message.company_id,  # MULTI-TENANT
            state=SessionState.INITIATED,
            ttl=settings.session_ttl
        )

        logger.info("new_session_created", session_id=session.id, company_id=message.company_id)
        return session
    
    async def _build_conversation_history(self, session: Session) -> List[Dict]:
        """
        Построить историю диалога для контекста

        Загружает историю из Redis (последние 20 сообщений)
        """
        history = await self.storage.get_conversation_history(
            session_id=session.id,
            max_messages=20
        )
        return history
    
    async def _process_gemini_response(
        self,
        response: Dict,
        session: Session,
        tool_manager  # MULTI-TENANT: передаем tool_manager как параметр
    ) -> Dict:
        """
        Обработка ответа от Gemini

        Если есть function call - выполняем его и запрашиваем ответ повторно
        """
        # Проверяем наличие function call
        if response.get("function_call"):
            func_call = response["function_call"]
            func_name = func_call["name"]
            func_args = func_call["args"]

            logger.info(
                "executing_function_call",
                function=func_name,
                args=func_args
            )

            # Выполняем функцию
            func_result = await tool_manager.execute_function(
                function_name=func_name,
                arguments=func_args
            )

            # Сохраняем результат в контекст сессии
            if "function_results" not in session.context:
                session.context["function_results"] = []

            session.context["function_results"].append({
                "function": func_name,
                "arguments": func_args,
                "result": func_result
            })

            return {
                "text": None,
                "function_called": True,
                "function_name": func_name,
                "function_result": func_result,
                "needs_followup": True  # Нужен повторный запрос к LLM
            }

        # Обычный текстовый ответ
        return {
            "text": response.get("text", "Извините, я не понял. Можете переформулировать?"),
            "function_called": False
        }
    
    async def _update_session_state(self, session: Session):
        """
        Обновление состояния сессии на основе контекста
        
        Логика переходов между состояниями
        """
        context = session.context
        
        # INITIATED -> GREETING
        if session.state == SessionState.INITIATED:
            session.state = SessionState.GREETING
        
        # GREETING -> COLLECTING_INFO (если клиент выразил намерение)
        elif session.state == SessionState.GREETING:
            if any(k in context for k in ["desired_service", "name", "phone"]):
                session.state = SessionState.COLLECTING_INFO
        
        # COLLECTING_INFO -> BOOKING (если есть вся необходимая информация)
        elif session.state == SessionState.COLLECTING_INFO:
            required_fields = ["name", "phone", "desired_service"]
            if all(context.get(field) for field in required_fields):
                session.state = SessionState.BOOKING
        
        # BOOKING -> CONFIRMING (если выбран слот)
        elif session.state == SessionState.BOOKING:
            if context.get("selected_slot"):
                session.state = SessionState.CONFIRMING
        
        # CONFIRMING -> COMPLETED (если создана запись)
        elif session.state == SessionState.CONFIRMING:
            if context.get("appointment_id"):
                session.state = SessionState.COMPLETED
    
    async def shutdown(self):
        """Корректное завершение работы"""
        await self.storage.disconnect()
        logger.info("orchestrator_shutdown")

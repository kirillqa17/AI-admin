"""
Google Gemini API Service

Использует новый google-genai SDK (google-generativeai deprecated с 30.11.2025)
"""

import asyncio
from typing import List, Dict, Any, Optional
from google import genai
from google.genai.types import GenerateContentConfig, Tool, FunctionDeclaration
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)


class GeminiService:
    """
    Сервис для работы с Google Gemini API
    
    Поддерживает:
    - Генерацию текста
    - Function calling
    - Управление контекстом диалога
    """
    
    def __init__(self):
        """Инициализация Gemini клиента"""
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        
        logger.info(
            "gemini_service_initialized",
            model=self.model,
            temperature=settings.temperature
        )
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Tool]] = None,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Генерация ответа от Gemini
        
        Args:
            messages: История диалога в формате [{"role": "user/model", "parts": [{"text": "..."}]}]
            tools: Список доступных функций для function calling
            system_instruction: Системный промпт
            
        Returns:
            Dict с ответом и метаданными
        """
        try:
            # Конфигурация генерации
            config = GenerateContentConfig(
                temperature=settings.temperature,
                max_output_tokens=settings.max_tokens,
                tools=tools if tools else None,
                system_instruction=system_instruction,
            )
            
            # Последнее сообщение пользователя
            user_message = messages[-1]["parts"][0]["text"] if messages else ""
            
            # Формируем контекст из предыдущих сообщений
            # В новом SDK используется contents вместо messages
            contents = self._format_messages_for_gemini(messages[:-1]) if len(messages) > 1 else None
            
            logger.debug(
                "generating_gemini_response",
                user_message_preview=user_message[:100],
                tools_count=len(tools) if tools else 0,
                has_system_instruction=system_instruction is not None
            )
            
            # Генерация ответа
            # В новом SDK метод называется models.generate_content
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=user_message,
                config=config
            )
            
            # Обработка ответа
            result = self._parse_response(response)
            
            logger.info(
                "gemini_response_generated",
                has_text=result.get("text") is not None,
                has_function_call=result.get("function_call") is not None,
                finish_reason=result.get("finish_reason")
            )
            
            return result
            
        except Exception as e:
            logger.error("gemini_generation_error", error=str(e), exc_info=True)
            raise
    
    def _format_messages_for_gemini(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Форматирование сообщений для Gemini API
        
        Args:
            messages: Список сообщений
            
        Returns:
            Отформатированные сообщения
        """
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg["role"],
                "parts": msg["parts"]
            })
        return formatted
    
    def _parse_response(self, response) -> Dict[str, Any]:
        """
        Парсинг ответа от Gemini
        
        Args:
            response: Ответ от Gemini API
            
        Returns:
            Структурированный ответ
        """
        result = {
            "finish_reason": None,
            "text": None,
            "function_call": None,
        }
        
        if not response.candidates:
            logger.warning("no_candidates_in_response")
            return result
        
        candidate = response.candidates[0]
        result["finish_reason"] = candidate.finish_reason
        
        if not candidate.content or not candidate.content.parts:
            logger.warning("no_content_parts_in_candidate")
            return result
        
        for part in candidate.content.parts:
            # Текстовый ответ
            if hasattr(part, 'text') and part.text:
                result["text"] = part.text
            
            # Function call
            if hasattr(part, 'function_call') and part.function_call:
                result["function_call"] = {
                    "name": part.function_call.name,
                    "args": dict(part.function_call.args) if part.function_call.args else {}
                }
        
        return result
    
    def create_function_declaration(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any]
    ) -> FunctionDeclaration:
        """
        Создание декларации функции для function calling
        
        Args:
            name: Имя функции
            description: Описание функции
            parameters: JSON Schema параметров
            
        Returns:
            FunctionDeclaration
        """
        return FunctionDeclaration(
            name=name,
            description=description,
            parameters=parameters
        )
    
    async def health_check(self) -> bool:
        """
        Проверка доступности Gemini API
        
        Returns:
            True если API доступен
        """
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents="Проверка связи. Ответь одним словом: OK"
            )
            return response.text is not None
        except Exception as e:
            logger.error("gemini_health_check_failed", error=str(e))
            return False

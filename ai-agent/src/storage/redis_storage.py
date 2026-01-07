"""
Redis Storage для управления сессиями диалогов
"""

import json
import redis.asyncio as aioredis
from typing import Optional
import structlog
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))
from models.session import Session

from ..config import settings

logger = structlog.get_logger(__name__)


class RedisStorage:
    """
    Redis хранилище для сессий диалогов
    
    Использует async Redis для хранения состояния диалогов
    """
    
    def __init__(self):
        """Инициализация Redis клиента"""
        self.redis: Optional[aioredis.Redis] = None
        self._initialized = False
    
    async def connect(self):
        """Подключение к Redis"""
        if self._initialized:
            return
        
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Проверка подключения
            await self.redis.ping()
            
            self._initialized = True
            logger.info("redis_connected", url=settings.redis_url)
            
        except Exception as e:
            logger.error("redis_connection_error", error=str(e), exc_info=True)
            raise
    
    async def disconnect(self):
        """Отключение от Redis"""
        if self.redis:
            await self.redis.close()
            self._initialized = False
            logger.info("redis_disconnected")
    
    def _get_session_key(self, session_id: str) -> str:
        """Формирует ключ для сессии в Redis"""
        return f"session:{session_id}"
    
    async def save_session(self, session: Session) -> bool:
        """
        Сохранить сессию в Redis
        
        Args:
            session: Объект сессии
            
        Returns:
            True если успешно сохранено
        """
        if not self._initialized:
            await self.connect()
        
        try:
            key = self._get_session_key(session.id)
            session_data = session.model_dump_json()
            
            # Сохраняем с TTL
            await self.redis.setex(
                key,
                session.ttl,
                session_data
            )
            
            logger.debug(
                "session_saved",
                session_id=session.id,
                state=session.state,
                ttl=session.ttl
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "session_save_error",
                session_id=session.id,
                error=str(e),
                exc_info=True
            )
            return False
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Получить сессию из Redis
        
        Args:
            session_id: ID сессии
            
        Returns:
            Session или None если не найдена
        """
        if not self._initialized:
            await self.connect()
        
        try:
            key = self._get_session_key(session_id)
            session_data = await self.redis.get(key)
            
            if not session_data:
                logger.debug("session_not_found", session_id=session_id)
                return None
            
            session = Session.model_validate_json(session_data)
            
            logger.debug(
                "session_loaded",
                session_id=session_id,
                state=session.state
            )
            
            return session
            
        except Exception as e:
            logger.error(
                "session_load_error",
                session_id=session_id,
                error=str(e),
                exc_info=True
            )
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Удалить сессию
        
        Args:
            session_id: ID сессии
            
        Returns:
            True если успешно удалено
        """
        if not self._initialized:
            await self.connect()
        
        try:
            key = self._get_session_key(session_id)
            result = await self.redis.delete(key)
            
            logger.info("session_deleted", session_id=session_id)
            return result > 0
            
        except Exception as e:
            logger.error(
                "session_delete_error",
                session_id=session_id,
                error=str(e),
                exc_info=True
            )
            return False
    
    async def update_session_ttl(self, session_id: str, ttl: int) -> bool:
        """
        Обновить TTL сессии
        
        Args:
            session_id: ID сессии
            ttl: Новый TTL в секундах
            
        Returns:
            True если успешно обновлено
        """
        if not self._initialized:
            await self.connect()
        
        try:
            key = self._get_session_key(session_id)
            await self.redis.expire(key, ttl)
            
            logger.debug("session_ttl_updated", session_id=session_id, ttl=ttl)
            return True
            
        except Exception as e:
            logger.error(
                "session_ttl_update_error",
                session_id=session_id,
                error=str(e)
            )
            return False
    
    async def health_check(self) -> bool:
        """
        Проверка здоровья Redis
        
        Returns:
            True если Redis доступен
        """
        try:
            if not self._initialized:
                await self.connect()
            
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error("redis_health_check_failed", error=str(e))
            return False

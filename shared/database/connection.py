"""
Database connection management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator


class Database:
    """Database connection manager"""
    
    def __init__(self, database_url: str):
        """
        Args:
            database_url: PostgreSQL URL (e.g., postgresql+asyncpg://user:pass@host/db)
        """
        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
        )
        
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager для сессий
        
        Usage:
            async with db.session() as session:
                result = await session.execute(...)
        """
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close database connection"""
        await self.engine.dispose()

"""
Async SQLModel database session and initialization utilities for VyRaTrader.
- Reads DATABASE_URL from env-based settings and coerces to asyncpg dialect if needed.
- Exposes `engine`, `async_session` factory, `init_db()` to create tables, and `get_session()` dependency.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.core.config import settings


def _coerce_asyncpg(url: str) -> str:
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL: str = _coerce_asyncpg(settings.DATABASE_URL)

# Create async engine
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

# Async session factory
async_session: sessionmaker[AsyncSession] = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables using SQLModel metadata.
    Alembic should be used for real migrations; this is safe for initial bootstrap/dev.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to provide an AsyncSession per request."""
    async with async_session() as session:
        yield session

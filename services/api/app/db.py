"""
Async SQLAlchemy engine, session factory, and FastAPI dependency.

Standards:
- Engine is created once at import time from settings.DATABASE_URL.
- Sessions are yielded by get_db_session; callers must not manage commit/rollback.
- Every error rolls back automatically; 2xx paths commit automatically.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# ── Engine ─────────────────────────────────────────────────────────────────────
# pool_pre_ping=True: validate connections before checkout (handles Postgres restarts)
# echo=False: SQL logging handled by structlog, not SQLAlchemy's built-in logger
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    future=True,
)

# ── Session factory ─────────────────────────────────────────────────────────────
# expire_on_commit=False: keeps ORM objects accessible after commit without
# triggering lazy-load errors in async context.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Alias used by workers to create sessions outside the FastAPI request lifecycle
async_session_factory = AsyncSessionLocal


# ── FastAPI dependency ─────────────────────────────────────────────────────────

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Commits on success, rolls back on any exception, always closes.
    Usage:
        async def my_endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

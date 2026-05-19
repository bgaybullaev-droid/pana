"""Database connection and session management.

Two async engines are exposed:

* ``engine`` / ``async_session_maker`` — the primary RW pool used by
  every API/admin/worker code path.
* ``seo_read_engine`` / ``seo_read_session_maker`` (Block F V2.0 F3a) —
  a dedicated read-only pool used by the SEO/SSR routes. Isolating
  these so a Googlebot/Yandexbot crawl burst against
  ``/{lang}/listing/…`` can never starve the API pool that user
  traffic depends on.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Block F V2.0 F3a — dedicated read-only engine for SEO/SSR routes.
# Pool intentionally smaller than the primary pool so a misbehaving
# crawler can't acquire all connections; max_overflow gives elasticity
# during legitimate spikes without unbounded growth.
seo_read_engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
)

seo_read_session_maker = async_sessionmaker(
    seo_read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_seo_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a session from the SEO read-only
    pool. Caller MUST treat the session as read-only — no writes,
    flushes, or commits — so the dedicated pool's isolation guarantees
    hold.
    """
    async with seo_read_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

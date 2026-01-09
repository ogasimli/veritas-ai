"""Database engine and session configuration."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

# Create async engine with connection health checks
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,  # Check connection health before using
    echo=settings.debug,  # Log SQL statements in debug mode
)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Required for async compatibility
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields database sessions."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

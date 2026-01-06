"""
Database configuration and connection management
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from core.config import settings

# Determine database type and configure accordingly
DATABASE_URL = settings.DATABASE_URL

# Check if using PostgreSQL or SQLite
if DATABASE_URL.startswith("postgresql://"):
    # Convert PostgreSQL URL to async version
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    # PostgreSQL-specific engine configuration
    engine = create_async_engine(
        DATABASE_URL,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        echo=settings.DB_ECHO or settings.DEBUG,
    )
elif DATABASE_URL.startswith("sqlite"):
    # SQLite async configuration (aiosqlite)
    # SQLite doesn't support connection pooling in the same way
    engine = create_async_engine(
        DATABASE_URL,
        poolclass=NullPool,  # SQLite works better without pooling
        echo=settings.DB_ECHO or settings.DEBUG,
        connect_args={"check_same_thread": False}  # Required for SQLite async
    )
else:
    # Fallback for other database types
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.DB_ECHO or settings.DEBUG,
    )

# Create async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for all models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
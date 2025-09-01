"""
Unified database connection management for DevCycle.

This module provides a single async-first database architecture with proper
connection pooling and session management using SQLAlchemy.
"""

from typing import Any, AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from ..config import get_config
from ..logging import get_logger

logger = get_logger("core.database")


def get_async_database_url() -> str:
    """
    Get async database connection URL from configuration.

    Returns:
        Async database connection string
    """
    config = get_config().database

    if config.password:
        return (
            f"postgresql+asyncpg://{config.username}:{config.password}"
            f"@{config.host}:{config.port}/{config.database}"
        )
    else:
        return (
            f"postgresql+asyncpg://{config.username}"
            f"@{config.host}:{config.port}/{config.database}"
        )


def get_async_engine() -> AsyncEngine:
    """
    Get unified async SQLAlchemy engine with async-compatible connection pooling.

    Returns:
        Configured async SQLAlchemy engine with NullPool (required for async)
    """
    config = get_config().database
    database_url = get_async_database_url()

    # Create async engine with async-compatible connection pooling
    engine = create_async_engine(
        database_url,
        poolclass=NullPool,  # Use NullPool for async engines (required by SQLAlchemy)
        echo=config.echo,  # SQL logging
    )

    # Add connection event listeners
    @event.listens_for(engine.sync_engine, "connect")
    def set_postgresql_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        """Set PostgreSQL-specific connection options."""
        if hasattr(dbapi_connection, "autocommit"):
            dbapi_connection.autocommit = False

    @event.listens_for(engine.sync_engine, "checkout")
    def receive_checkout(
        dbapi_connection: Any, connection_record: Any, connection_proxy: Any
    ) -> None:
        """Log connection checkout."""
        logger.debug("Database connection checked out")

    @event.listens_for(engine.sync_engine, "checkin")
    def receive_checkin(dbapi_connection: Any, connection_record: Any) -> None:
        """Log connection checkin."""
        logger.debug("Database connection checked in")

    return engine


# Create unified async session factory - will be initialized lazily
AsyncSessionLocal = None


def _get_async_session_local() -> Any:
    """Get or create the unified async session local factory."""
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = async_sessionmaker(
            autocommit=False, autoflush=False, bind=get_async_engine()
        )
    return AsyncSessionLocal


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get unified async database session.

    Yields:
        Async database session instance
    """
    session_local = _get_async_session_local()
    async with session_local() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """Initialize database and create tables using async engine."""
    from .models import Base

    engine = get_async_engine()

    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def close_database() -> None:
    """Close database connections."""
    engine = get_async_engine()
    await engine.dispose()
    logger.info("Database connections closed")


def reset_database_factories() -> None:
    """Reset database session factories to force reinitialization with new config."""
    global AsyncSessionLocal
    AsyncSessionLocal = None
    logger.info("Database session factories reset")

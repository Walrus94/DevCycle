"""
Database connection management for DevCycle.

This module provides database connection utilities, connection pooling,
and session management using SQLAlchemy.
"""

from contextlib import contextmanager
from typing import Any, AsyncGenerator, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from ..config import get_config
from ..logging import get_logger

logger = get_logger("core.database")


def get_database_url() -> str:
    """
    Get database connection URL from configuration.

    Returns:
        Database connection string
    """
    config = get_config().database

    if config.password:
        return f"postgresql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
    else:
        return f"postgresql://{config.username}@{config.host}:{config.port}/{config.database}"


def get_engine() -> Engine:
    """
    Get SQLAlchemy engine with connection pooling.

    Returns:
        Configured SQLAlchemy engine
    """
    config = get_config().database
    database_url = get_database_url()

    # Create engine with connection pooling
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,  # Recycle connections every hour
        echo=config.echo,  # SQL logging
    )

    # Add connection event listeners
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        """Set PostgreSQL-specific connection options."""
        if hasattr(dbapi_connection, "autocommit"):
            dbapi_connection.autocommit = False

    @event.listens_for(engine, "checkout")
    def receive_checkout(
        dbapi_connection: Any, connection_record: Any, connection_proxy: Any
    ) -> None:
        """Log connection checkout."""
        logger.debug("Database connection checked out")

    @event.listens_for(engine, "checkin")
    def receive_checkin(dbapi_connection: Any, connection_record: Any) -> None:
        """Log connection checkin."""
        logger.debug("Database connection checked in")

    return engine


# Create session factory - will be initialized lazily
SessionLocal = None


def _get_session_local() -> Any:
    """Get or create the session local factory."""
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return SessionLocal


def get_session() -> Session:
    """
    Get database session.

    Returns:
        Database session instance
    """
    session_local = _get_session_local()
    return session_local()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Yields:
        Database session instance

    Example:
        with get_db_session() as session:
            user = session.query(User).first()
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    """Initialize database and create tables."""
    from .models import Base

    engine = get_engine()

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def close_database() -> None:
    """Close database connections."""
    engine = get_engine()
    engine.dispose()
    logger.info("Database connections closed")


def reset_database_factories() -> None:
    """Reset database session factories to force reinitialization with new config."""
    global SessionLocal, AsyncSessionLocal
    SessionLocal = None
    AsyncSessionLocal = None
    logger.info("Database session factories reset")


# Async database support for FastAPI Users
def get_async_database_url() -> str:
    """
    Get async database connection URL from configuration.

    Returns:
        Async database connection string
    """
    config = get_config().database

    if config.password:
        return f"postgresql+asyncpg://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
    else:
        return f"postgresql+asyncpg://{config.username}@{config.host}:{config.port}/{config.database}"


def get_async_engine() -> Any:
    """
    Get async SQLAlchemy engine with connection pooling.

    Returns:
        Configured async SQLAlchemy engine
    """
    config = get_config().database
    database_url = get_async_database_url()

    # Create async engine with connection pooling
    engine = create_async_engine(
        database_url,
        poolclass=NullPool,  # Use NullPool for async engines
        echo=config.echo,  # SQL logging
    )

    return engine


# Create async session factory - will be initialized lazily
AsyncSessionLocal = None


def _get_async_session_local() -> Any:
    """Get or create the async session local factory."""
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = async_sessionmaker(
            autocommit=False, autoflush=False, bind=get_async_engine()
        )
    return AsyncSessionLocal


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session.

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

"""
Testcontainers-based fixtures for DevCycle tests.

This module provides database and container fixtures using testcontainers
for integration and e2e tests. This is much better than the Docker setup
as it provides better isolation and automatic cleanup.
"""

from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer  # type: ignore

from devcycle.core.dependencies import get_async_session

# We'll create the app with proper configuration
app = None


@pytest.fixture(scope="session")
def test_app():
    """Create the test app with the test environment."""
    global app
    from devcycle.api.app import create_app

    app = create_app(environment="testing")
    return app


@pytest.fixture(scope="session")
def postgres_container():
    """Create a PostgreSQL container for testing."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        # Wait for the container to be ready
        postgres.get_connection_url()
        yield postgres


@pytest.fixture(scope="session")
def test_db_url(postgres_container):
    """Get the test database URL from the container."""
    # Convert the sync URL to async
    sync_url = postgres_container.get_connection_url()

    # Handle different URL formats
    if sync_url.startswith("postgresql+psycopg2://"):
        async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    elif sync_url.startswith("postgresql://"):
        async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://")
    elif sync_url.startswith("postgres://"):
        async_url = sync_url.replace("postgres://", "postgresql+asyncpg://")
    else:
        async_url = sync_url

    return async_url


@pytest.fixture(scope="session")
async def test_db_engine(test_db_url):
    """Create a test database engine using testcontainers."""
    engine = create_async_engine(test_db_url, echo=False)

    # Test connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))

    # Run database migrations to set up schema
    await run_database_migrations(engine)

    yield engine

    await engine.dispose()


async def run_database_migrations(engine):
    """Set up the database schema directly using SQLAlchemy."""
    from sqlalchemy import text

    # Create the database schema directly
    async with engine.begin() as conn:
        # Create user table (FastAPI Users base table)
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS "user" (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(320) NOT NULL UNIQUE,
                hashed_password VARCHAR(1024) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                is_superuser BOOLEAN NOT NULL DEFAULT false,
                is_verified BOOLEAN NOT NULL DEFAULT false,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                role VARCHAR(50) NOT NULL DEFAULT 'user',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """
            )
        )

        # Create agents table
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS agents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL UNIQUE,
                agent_type VARCHAR(50) NOT NULL,
                description TEXT,
                version VARCHAR(20) NOT NULL,
                capabilities TEXT NOT NULL,
                configuration TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'offline',
                is_active BOOLEAN NOT NULL DEFAULT true,
                last_heartbeat TIMESTAMP WITH TIME ZONE,
                response_time_ms INTEGER,
                error_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                uptime_seconds INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP WITH TIME ZONE
            )
        """
            )
        )

        # Create agent_tasks table
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS agent_tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                task_type VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL,
                parameters TEXT NOT NULL,
                result TEXT,
                error TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP WITH TIME ZONE,
                completed_at TIMESTAMP WITH TIME ZONE
            )
        """
            )
        )

        # Create agent_health table
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS agent_health (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                status VARCHAR(50) NOT NULL,
                last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                health_data JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """
            )
        )

        # Create alembic_version table for future migrations
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        """
            )
        )

        # Insert the current migration version
        await conn.execute(
            text(
                """
            INSERT INTO alembic_version (version_num)
            VALUES ('001')
            ON CONFLICT (version_num) DO NOTHING
        """
            )
        )

        print("Database schema initialized successfully")


@pytest.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def async_client(test_db_session, test_app) -> AsyncClient:
    """Create an async test client."""

    # Override the database dependency
    async def override_get_async_session():
        yield test_db_session

    test_app.dependency_overrides[get_async_session] = override_get_async_session

    client = AsyncClient(app=test_app, base_url="http://test")

    return client


@pytest.fixture
def client(async_client) -> AsyncClient:
    """Create a sync test client (alias for async_client for compatibility)."""
    return async_client


@pytest.fixture
async def authenticated_client(async_client, test_db_session) -> AsyncClient:
    """Create an authenticated test client with a test user."""
    from passlib.context import CryptContext
    from sqlalchemy import text

    # Create password context for hashing
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Create a test user directly in the database
    hashed_password = pwd_context.hash("TestPass123!")

    # Insert user directly into database
    await test_db_session.execute(
        text(
            """
            INSERT INTO "user" (email, hashed_password, is_active, is_superuser,
                               is_verified, role)
            VALUES (:email, :hashed_password, :is_active, :is_superuser,
                   :is_verified, :role)
        """
        ),
        {
            "email": "testuser@example.com",
            "hashed_password": hashed_password,
            "is_active": True,
            "is_superuser": False,
            "is_verified": True,
            "role": "user",
        },
    )
    await test_db_session.commit()

    # Login to get token
    login_response = await async_client.post(
        "/api/v1/auth/jwt/login",
        data={"username": "testuser@example.com", "password": "TestPass123!"},
    )

    token = login_response.json()["access_token"]

    # Set the authorization header for all requests
    async_client.headers.update({"Authorization": f"Bearer {token}"})

    return async_client


@pytest.fixture(autouse=True)
async def cleanup_test_data(test_db_session):
    """Clean up test data after each test."""
    yield
    # Clean up test data after each test
    try:
        # Check if we're already in a transaction
        if test_db_session.in_transaction():
            await test_db_session.rollback()

        # Clear all tables to ensure test isolation
        async with test_db_session.begin():
            # Check if tables exist before trying to delete from them
            try:
                # Check if agents table exists
                result = await test_db_session.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables "
                        "WHERE table_name = 'agents')"
                    )
                )
                agents_exists = result.scalar()

                if agents_exists:
                    await test_db_session.execute(text("DELETE FROM agents"))

                # Check if users table exists
                result = await test_db_session.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables "
                        "WHERE table_name = 'users')"
                    )
                )
                users_exists = result.scalar()

                if users_exists:
                    await test_db_session.execute(text('DELETE FROM "users"'))

                # Also check for any other tables that might contain test data
                result = await test_db_session.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
                tables = [row[0] for row in result.fetchall()]

                for table in tables:
                    if table not in ["agents", "users"] and not table.startswith(
                        "alembic_"
                    ):
                        # Clear any other tables that might contain test data
                        # Quote table names to handle reserved keywords
                        await test_db_session.execute(text(f'DELETE FROM "{table}"'))

                await test_db_session.commit()
            except Exception as e:
                # Log but don't fail - tables might not exist yet
                print(f"Table cleanup warning: {e}")
                await test_db_session.rollback()
    except Exception as e:
        # Log but don't fail the test
        print(f"Cleanup warning: {e}")
        try:
            await test_db_session.rollback()
        except Exception:
            pass

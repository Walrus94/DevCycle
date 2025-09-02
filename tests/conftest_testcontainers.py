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
from testcontainers.redis import RedisContainer  # type: ignore

from devcycle.core.dependencies import get_async_session

# We'll create the app with proper configuration
app = None


@pytest.fixture(scope="session")
def test_app(test_redis_url):
    """Create the test app with the test environment."""
    print("🏗️  Creating test application...")
    global app
    try:
        import os

        from devcycle.api.app import create_app

        print("📱 Creating app with testing environment...")

        # Set Redis environment variables for testing
        redis_host, redis_port = test_redis_url.replace("redis://", "").split(":")
        os.environ["REDIS_HOST"] = redis_host
        os.environ["REDIS_PORT"] = redis_port
        os.environ["REDIS_PASSWORD"] = ""  # No password for test Redis
        os.environ["REDIS_DB"] = "0"

        app = create_app(environment="testing")
        print("✅ Test application created successfully")
        return app
    except Exception as e:
        print(f"❌ Error creating test app: {e}")
        raise


@pytest.fixture(scope="session")
def postgres_container():
    """Create a PostgreSQL container for testing."""
    print("🔧 Starting PostgreSQL container setup...")
    try:
        print("📦 Creating PostgresContainer with postgres:15-alpine...")
        with PostgresContainer("postgres:15-alpine") as postgres:
            print("⏳ Waiting for container to be ready...")
            # Wait for the container to be ready
            connection_url = postgres.get_connection_url()
            print(f"✅ Container ready! Connection URL: {connection_url}")
            yield postgres
            print("🧹 Cleaning up PostgreSQL container...")
    except Exception as e:
        print(f"❌ Error setting up PostgreSQL container: {e}")
        raise


@pytest.fixture(scope="session")
def redis_container():
    """Create a Redis container for testing."""
    print("🔧 Starting Redis container setup...")
    try:
        print("📦 Creating RedisContainer with redis:7-alpine...")
        with RedisContainer("redis:7-alpine") as redis:
            print("⏳ Waiting for Redis container to be ready...")
            # Wait for the container to be ready
            # RedisContainer doesn't have get_connection_url(), so we construct it
            host = redis.get_container_host_ip()
            port = redis.get_exposed_port(6379)
            connection_url = f"redis://{host}:{port}"
            print(f"✅ Redis container ready! Connection URL: {connection_url}")
            yield redis
            print("🧹 Cleaning up Redis container...")
    except Exception as e:
        print(f"❌ Error setting up Redis container: {e}")
        raise


@pytest.fixture(scope="session")
def test_db_url(postgres_container):
    """Get the test database URL from the container."""
    print("🔗 Getting test database URL...")
    # Convert the sync URL to async
    sync_url = postgres_container.get_connection_url()
    print(f"📡 Sync URL: {sync_url}")

    # Handle different URL formats
    if sync_url.startswith("postgresql+psycopg2://"):
        async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    elif sync_url.startswith("postgresql://"):
        async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://")
    elif sync_url.startswith("postgres://"):
        async_url = sync_url.replace("postgres://", "postgresql+asyncpg://")
    else:
        async_url = sync_url

    print(f"🔄 Async URL: {async_url}")
    return async_url


@pytest.fixture(scope="session")
def test_redis_url(redis_container):
    """Get the test Redis URL from the container."""
    print("🔗 Getting test Redis URL...")
    # RedisContainer doesn't have get_connection_url(), so we construct it manually
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    redis_url = f"redis://{host}:{port}"
    print(f"📡 Redis URL: {redis_url}")
    return redis_url


@pytest.fixture(scope="session")
async def test_db_engine(test_db_url):
    """Create a test database engine using testcontainers."""
    print("🚀 Creating test database engine...")
    try:
        engine = create_async_engine(test_db_url, echo=False)
        print("✅ Engine created successfully")

        # Test connection
        print("🔍 Testing database connection...")
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection test successful")

        # Run database migrations to set up schema
        print("📋 Running database migrations...")
        await run_database_migrations(engine)
        print("✅ Database migrations completed")

        yield engine
        print("🧹 Disposing database engine...")
        await engine.dispose()
        print("✅ Database engine disposed")
    except Exception as e:
        print(f"❌ Error with database engine: {e}")
        raise


async def run_database_migrations(engine):
    """Set up the database schema directly using SQLAlchemy."""
    from sqlalchemy import text

    print("🏗️  Setting up database schema...")
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

        print("✅ Database schema initialized successfully")


@pytest.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    print("🔧 Creating test database session...")
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        print("✅ Test database session created")
        yield session
        print("🧹 Test database session closed")


@pytest.fixture
def async_client(test_db_session, test_app) -> AsyncClient:
    """Create an async test client."""
    print("🌐 Creating async test client...")

    # Override the database dependency
    async def override_get_async_session():
        yield test_db_session

    test_app.dependency_overrides[get_async_session] = override_get_async_session

    client = AsyncClient(app=test_app, base_url="http://test")
    print("✅ Async test client created")

    return client


@pytest.fixture
def client(async_client) -> AsyncClient:
    """Create a sync test client (alias for async_client for compatibility)."""
    return async_client


@pytest.fixture
async def authenticated_client(async_client, test_db_session) -> AsyncClient:
    """Create an authenticated test client with a test user."""
    print("🔐 Creating authenticated test client...")
    from passlib.context import CryptContext
    from sqlalchemy import text

    try:
        # Create password context for hashing
        print("🔑 Creating password context...")
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Create a test user directly in the database
        print("👤 Creating test user...")
        hashed_password = pwd_context.hash("TestPass123!")

        # Insert user directly into database
        print("💾 Inserting test user into database...")
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
        print("✅ Test user created successfully")

        # Login to get token
        print("🔑 Logging in to get authentication token...")
        print("🌐 Making request to: /api/v1/auth/jwt/login")
        print("📧 Username: testuser@example.com")

        try:
            print("⏰ Making login request with 30 second timeout...")
            import asyncio

            login_response = await asyncio.wait_for(
                async_client.post(
                    "/api/v1/auth/jwt/login",
                    data={
                        "username": "testuser@example.com",
                        "password": "TestPass123!",
                    },
                ),
                timeout=30.0,
            )
            print(f"📡 Login response status: {login_response.status_code}")
            print(f"📄 Login response text: {login_response.text}")
        except asyncio.TimeoutError:
            print("❌ Login request timed out after 30 seconds")
            raise Exception("Login request timed out")
        except Exception as e:
            print(f"❌ Exception during login request: {e}")
            raise

        if login_response.status_code != 200:
            print(
                f"❌ Login failed with status {login_response.status_code}: "
                f"{login_response.text}"
            )
            raise Exception(f"Login failed: {login_response.text}")

        try:
            token = login_response.json()["access_token"]
            print("✅ Authentication token obtained")
        except Exception as e:
            print(f"❌ Error parsing login response: {e}")
            print(f"📄 Response content: {login_response.text}")
            raise

        # Set the authorization header for all requests
        async_client.headers.update({"Authorization": f"Bearer {token}"})
        print("✅ Authenticated test client ready")

        return async_client
    except Exception as e:
        print(f"❌ Error creating authenticated client: {e}")
        raise


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

"""
Testcontainers-based fixtures for DevCycle tests.

This module provides database and container fixtures using testcontainers
for integration and e2e tests. This is much better than the Docker setup
as it provides better isolation and automatic cleanup.
"""

from typing import cast

import pytest
from httpx import AsyncClient
from testcontainers.postgres import PostgresContainer  # type: ignore
from testcontainers.redis import RedisContainer  # type: ignore
from tortoise import Tortoise
from tortoise.transactions import in_transaction

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
async def test_tortoise_config(test_db_url):
    """Create a test Tortoise ORM configuration."""
    print("🚀 Creating test Tortoise ORM configuration...")
    try:
        # Convert asyncpg URL to tortoise format
        # Tortoise expects postgres:// not postgresql://
        tortoise_url = test_db_url.replace("postgresql+asyncpg://", "postgres://")

        tortoise_config = {
            "connections": {"default": tortoise_url},
            "apps": {
                "models": {
                    "models": [
                        "devcycle.core.models.tortoise_models",
                        "devcycle.core.auth.tortoise_models",
                        "aerich.models",
                    ],
                    "default_connection": "default",
                },
            },
        }

        print("✅ Tortoise configuration created successfully")
        return tortoise_config
    except Exception as e:
        print(f"❌ Error creating Tortoise configuration: {e}")
        raise


@pytest.fixture(scope="session")
async def test_tortoise_init(test_tortoise_config):
    """Initialize Tortoise ORM for testing."""
    print("🚀 Initializing Tortoise ORM...")
    try:
        await Tortoise.init(config=test_tortoise_config)
        print("✅ Tortoise ORM initialized successfully")

        # Generate database schema
        print("📋 Generating database schema...")
        await Tortoise.generate_schemas()
        print("✅ Database schema generated")

        yield

        print("🧹 Closing Tortoise ORM connections...")
        await Tortoise.close_connections()
        print("✅ Tortoise ORM connections closed")
    except Exception as e:
        print(f"❌ Error with Tortoise ORM: {e}")
        raise


@pytest.fixture
async def test_db_transaction(test_tortoise_init):
    """Create a test database transaction."""
    print("🔧 Creating test database transaction...")
    async with in_transaction() as connection:
        print("✅ Test database transaction created")
        yield connection
        print("🧹 Test database transaction closed")


@pytest.fixture
def async_client(test_tortoise_init, test_app) -> AsyncClient:
    """Create an async test client."""
    print("🌐 Creating async test client...")

    client = AsyncClient(app=test_app, base_url="http://test")
    print("✅ Async test client created")

    return client


@pytest.fixture
def client(async_client) -> AsyncClient:
    """Create a test client.

    This is an alias for async_client for compatibility.
    """
    return cast(AsyncClient, async_client)


@pytest.fixture
async def authenticated_client(async_client, test_tortoise_init) -> AsyncClient:
    """Create an authenticated test client with a test user."""
    print("🔐 Creating authenticated test client...")
    from passlib.context import CryptContext

    from devcycle.core.auth.tortoise_models import User

    try:
        # Create password context for hashing
        print("🔑 Creating password context...")
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Create a test user using Tortoise ORM
        print("👤 Creating test user...")
        hashed_password = pwd_context.hash("TestPass123!")

        # Create user using Tortoise ORM
        print("💾 Creating test user with Tortoise ORM...")
        _ = await User.create(
            email="testuser@example.com",
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=False,
            is_verified=True,
            role="user",
        )
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

        return cast(AsyncClient, async_client)
    except Exception as e:
        print(f"❌ Error creating authenticated client: {e}")
        raise


@pytest.fixture(autouse=True)
async def cleanup_test_data(test_tortoise_init):
    """Clean up test data after each test."""
    yield
    # Clean up test data after each test
    try:
        from devcycle.core.auth.tortoise_models import User
        from devcycle.core.models.tortoise_models import Agent, AgentHealth, AgentTask

        # Clear all test data using Tortoise ORM
        print("🧹 Cleaning up test data...")

        # Delete all records from all tables
        await AgentHealth.all().delete()
        await AgentTask.all().delete()
        await Agent.all().delete()
        await User.all().delete()

        print("✅ Test data cleaned up successfully")
    except Exception as e:
        # Log but don't fail the test
        print(f"Cleanup warning: {e}")
        pass

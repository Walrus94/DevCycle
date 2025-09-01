"""
Pytest configuration and fixtures for DevCycle tests.
"""

import asyncio
import time
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from devcycle.core.dependencies import get_async_session
from devcycle.core.repositories.agent_repository import (
    AgentRepository,
    AgentTaskRepository,
)
from devcycle.core.repositories.user_repository import UserRepository
from devcycle.core.services.agent_service import AgentService
from devcycle.core.services.user_service import UserService

# We'll create the app with proper configuration
app = None


# Configure pytest-docker
def pytest_configure(config):
    """Configure pytest with Docker settings."""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test requiring Docker"
    )


@pytest.fixture(scope="session")
def test_app():
    """Create the test app with the test environment."""
    global app
    from devcycle.api.app import create_app

    app = create_app(environment="test")
    return app


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Return the path to the test Docker Compose file."""
    return "docker-compose.test.yml"


@pytest.fixture(scope="session")
def docker_services(docker_compose_file):
    """Start Docker services for e2e tests."""
    # pytest-docker will automatically start services and wait for health checks
    # This fixture ensures services are running before tests begin
    pass


@pytest.fixture(scope="session")
def docker_services_ready(docker_services):
    """Ensure all Docker services are ready before running tests."""
    # Wait a bit more for services to be fully ready
    time.sleep(5)
    return docker_services


@pytest.fixture(scope="session")
async def clean_database_at_start():
    """Clean the database at the start of the test session."""
    # Create a separate engine for session-level cleanup
    test_db_url = (
        "postgresql+asyncpg://test_user:test_password@localhost:5434/devcycle_test"
    )
    engine = create_async_engine(test_db_url, echo=False)

    async with engine.begin() as conn:
        # Check if tables exist before trying to delete from them
        try:
            # Check if agents table exists
            result = await conn.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'agents')"
                )
            )
            agents_exists = result.scalar()

            if agents_exists:
                await conn.execute(text("DELETE FROM agents"))

            # Check if users table exists
            result = await conn.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'users')"
                )
            )
            users_exists = result.scalar()

            if users_exists:
                await conn.execute(text('DELETE FROM "users"'))

            # Also check for any other tables that might contain test data
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            tables = [row[0] for row in result.fetchall()]

            for table in tables:
                if table not in ["agents", "users"] and not table.startswith(
                    "alembic_"
                ):
                    # Clear any other tables that might contain test data
                    # Quote table names to handle reserved keywords
                    await conn.execute(text(f'DELETE FROM "{table}"'))

            await conn.commit()
        except Exception as e:
            # Log but don't fail - tables might not exist yet
            print(f"Database cleanup warning: {e}")
            await conn.rollback()

    await engine.dispose()
    yield


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_engine(docker_services_ready, clean_database_at_start):
    """Create a test database engine."""
    # Use test database URL
    test_db_url = (
        "postgresql+asyncpg://test_user:test_password@localhost:5434/devcycle_test"
    )

    # Wait for database to be ready
    max_retries = 10
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            engine = create_async_engine(test_db_url, echo=False)
            # Test connection
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(
                    f"Database connection failed after {max_retries} attempts: {e}"
                )
            print(
                f"Database connection attempt {attempt + 1} failed, "
                f"retrying in {retry_delay}s..."
            )
            await asyncio.sleep(retry_delay)

    yield engine

    await engine.dispose()


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

    # Clean up will be handled by the test
    return client


# Add a sync client fixture for tests that need it
@pytest.fixture
def client(async_client) -> AsyncClient:
    """Create a sync test client (alias for async_client for compatibility)."""
    return async_client


@pytest.fixture
def mock_user_repository():
    """Create a mock user repository for unit tests."""
    from unittest.mock import AsyncMock

    return AsyncMock(spec=UserRepository)


@pytest.fixture
def mock_agent_repository():
    """Create a mock agent repository for unit tests."""
    from unittest.mock import AsyncMock

    return AsyncMock(spec=AgentRepository)


@pytest.fixture
def mock_agent_task_repository():
    """Create a mock agent task repository for unit tests."""
    from unittest.mock import AsyncMock

    return AsyncMock(spec=AgentTaskRepository)


@pytest.fixture
def mock_user_service(mock_user_repository):
    """Create a mock user service for unit tests."""
    from unittest.mock import AsyncMock

    return AsyncMock(spec=UserService)


@pytest.fixture
def mock_agent_service(mock_agent_repository, mock_agent_task_repository):
    """Create a mock agent service for unit tests."""
    from unittest.mock import AsyncMock

    return AsyncMock(spec=AgentService)


# Test isolation fixtures
@pytest.fixture(autouse=True)
async def test_isolation():
    """Add isolation between tests."""
    yield
    # Add a small delay between tests for stability
    await asyncio.sleep(0.1)


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
                    print("Cleaned up users table")

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
                print(f"Database cleanup completed. Tables found: {tables}")
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


# Test markers
def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their location."""
    for item in items:
        # Mark tests in e2e directory as e2e tests
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        # Mark tests in integration directory as integration tests
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        # Mark tests in unit directory as unit tests
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

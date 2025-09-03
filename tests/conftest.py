"""
Pytest configuration and fixtures for DevCycle tests.

This module provides common test fixtures that are used across all test types.
It does NOT include database or Docker fixtures to keep unit tests fast.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from devcycle.core.services.agent_service import AgentService


# Configure pytest-docker
def pytest_configure(config):
    """Configure pytest with Docker settings."""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test requiring Docker"
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_agent_service():
    """Create a mock agent service for unit tests."""
    return AsyncMock(spec=AgentService)


@pytest.fixture
def mock_agent_repository():
    """Create a mock agent repository for unit tests."""
    mock_repo = AsyncMock()
    # Add common repository methods
    mock_repo.get_by_id = AsyncMock()
    mock_repo.get_by_name = AsyncMock()
    mock_repo.create = AsyncMock()
    mock_repo.update = AsyncMock()
    mock_repo.delete = AsyncMock()
    mock_repo.list_all = AsyncMock()
    return mock_repo


# Test isolation fixtures
@pytest.fixture(autouse=True)
async def test_isolation():
    """Add isolation between tests."""
    yield
    # Add a small delay between tests for stability
    await asyncio.sleep(0.01)  # Reduced from 0.1s to 0.01s


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

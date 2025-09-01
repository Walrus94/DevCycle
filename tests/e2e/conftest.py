"""
End-to-end test configuration and fixtures for DevCycle.

This module provides common test fixtures and configuration
for end-to-end tests using testcontainers.
"""

from unittest.mock import Mock

import pytest

from devcycle.core.config import DevCycleConfig

# Import testcontainers fixtures for e2e tests
from ..conftest_testcontainers import *  # noqa: F401, F403


@pytest.fixture(scope="session")
def mock_config() -> DevCycleConfig:
    """Mock configuration for testing."""
    mock_config_instance = Mock(spec=DevCycleConfig)
    mock_config_instance.database.host = "localhost"
    mock_config_instance.database.port = 5432
    mock_config_instance.database.username = "test_user"
    mock_config_instance.database.password = "test_password"
    mock_config_instance.database.database = "devcycle_test"
    mock_config_instance.database.pool_size = 5
    mock_config_instance.database.max_overflow = 10
    mock_config_instance.database.echo = False

    mock_config_instance.api.host = "localhost"
    mock_config_instance.api.port = 8000
    mock_config_instance.api.debug = True
    mock_config_instance.api.reload = False

    mock_config_instance.redis.host = "localhost"
    mock_config_instance.redis.port = 6379
    mock_config_instance.redis.db = 0
    mock_config_instance.redis.password = None

    mock_config_instance.logging.level = "DEBUG"
    mock_config_instance.logging.format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    mock_config_instance.logging.json_output = False
    mock_config_instance.logging.log_file = None

    mock_config_instance.huggingface.token = "test_token"
    mock_config_instance.huggingface.organization = "test_org"
    mock_config_instance.huggingface.space_name = "test_space"

    return mock_config_instance


@pytest.fixture(scope="session")
def mock_config_instance(mock_config: DevCycleConfig) -> DevCycleConfig:
    """Mock configuration instance for testing."""
    return mock_config


@pytest.fixture(scope="session")
def sample_user_data() -> dict:
    """Sample user data for testing."""
    return {"email": "testuser@example.com", "password": "SecurePassword123!"}


@pytest.fixture(scope="session")
def sample_user_response() -> dict:
    """Sample user response data for testing."""
    return {
        "id": "test_user_id",
        "email": "testuser@example.com",
        "is_active": True,
        "is_superuser": False,
        "is_verified": False,
    }


@pytest.fixture(scope="session")
def sample_agent_data() -> dict:
    """Sample agent data for testing."""
    return {"name": "test_agent", "type": "test_type", "config": {"param1": "value1"}}


@pytest.fixture(scope="session")
def sample_agent_response() -> dict:
    """Sample agent response data for testing."""
    return {
        "id": "test_agent_id",
        "name": "test_agent",
        "type": "test_type",
        "status": "offline",
        "config": {"param1": "value1"},
        "capabilities": ["test_capability"],
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
    }


@pytest.fixture(scope="session")
def sample_message_data() -> dict:
    """Sample message data for testing."""
    return {
        "action": "test_action",
        "data": {"key": "value"},
        "priority": "normal",
        "ttl": 300,
    }


@pytest.fixture(scope="session")
def sample_message_response() -> dict:
    """Sample message response data for testing."""
    return {
        "id": "test_message_id",
        "action": "test_action",
        "data": {"key": "value"},
        "priority": "normal",
        "ttl": 300,
        "status": "pending",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
    }


@pytest.fixture(scope="session")
def sample_session_data() -> dict:
    """Sample session data for testing."""
    return {"user_id": "test_user_id", "email": "testuser@example.com"}

"""
Integration test configuration and fixtures for DevCycle.

This module provides common test fixtures and configuration
for integration tests.
"""

from unittest.mock import Mock

import pytest

from devcycle.core.config import DevCycleConfig


@pytest.fixture(scope="session")
def mock_config() -> DevCycleConfig:
    """Mock configuration for testing."""
    mock_config_instance = Mock(spec=DevCycleConfig)

    # Mock logging config
    mock_config_instance.logging.level = "DEBUG"
    mock_config_instance.logging.json_output = False
    mock_config_instance.logging.log_file = None

    # Mock database config
    mock_config_instance.database.host = "localhost"
    mock_config_instance.database.port = 5432
    mock_config_instance.database.username = "test"
    mock_config_instance.database.password = "test"
    mock_config_instance.database.database = "test_db"
    mock_config_instance.database.echo = False

    # Mock API config
    mock_config_instance.api.host = "127.0.0.1"
    mock_config_instance.api.port = 8000
    mock_config_instance.api.reload = False
    mock_config_instance.api.cors_origins = ["*"]
    mock_config_instance.api.cors_credentials = True
    mock_config_instance.api.cors_methods = ["*"]
    mock_config_instance.api.cors_headers = ["*"]

    # Mock HuggingFace config
    mock_config_instance.huggingface.token = "test_token"
    mock_config_instance.huggingface.org_name = "test_org"

    # Mock agent config
    mock_config_instance.agent.max_execution_time = 300
    mock_config_instance.agent.max_memory_usage = 1024
    mock_config_instance.agent.enable_logging = True
    mock_config_instance.agent.enable_metrics = True
    mock_config_instance.agent.model_name = "test-model"
    mock_config_instance.agent.temperature = 0.7
    mock_config_instance.agent.max_tokens = 1000
    mock_config_instance.agent.max_retries = 3
    mock_config_instance.agent.retry_delay = 1.0

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
        "id": "test-user-id",
        "email": "testuser@example.com",
        "is_active": True,
        "is_verified": False,
        "is_superuser": False,
    }


@pytest.fixture(scope="session")
def sample_agent_data() -> dict:
    """Sample agent data for testing."""
    return {"name": "test_agent", "type": "test_type", "config": {"param1": "value1"}}


@pytest.fixture(scope="session")
def sample_agent_response() -> dict:
    """Sample agent response data for testing."""
    return {
        "id": "test-agent-id",
        "name": "test_agent",
        "type": "test_type",
        "status": "idle",
        "config": {"param1": "value1"},
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture(scope="session")
def sample_message_data() -> dict:
    """Sample message data for testing."""
    return {
        "content": "Test message content",
        "sender": "test_sender",
        "recipient": "test_recipient",
        "message_type": "text",
    }


@pytest.fixture(scope="session")
def sample_message_response() -> dict:
    """Sample message response data for testing."""
    return {
        "id": "test-message-id",
        "content": "Test message content",
        "sender": "test_sender",
        "recipient": "test_recipient",
        "message_type": "text",
        "timestamp": "2024-01-01T00:00:00Z",
        "status": "sent",
    }


@pytest.fixture(scope="session")
def sample_session_data() -> dict:
    """Sample session data for testing."""
    return {"user_id": "test_user_id", "email": "testuser@example.com"}

"""Centralized configuration for E2E tests using the unified config system."""

from devcycle.core.config import get_config


def get_test_config() -> dict:
    """Get test configuration from unified config system."""
    config = get_config()
    return {
        "database_url": config.get_async_database_url(),
        "api_host": config.api.host,
        "api_port": config.api.port,
        "test_timeout": config.test.test_timeout,
        "parallel_workers": config.test.parallel_workers,
        "retry_attempts": config.test.retry_attempts,
        "log_level": config.logging.level,
    }


def get_test_database_url() -> str:
    """Get test database URL."""
    config = get_config()
    return config.get_async_database_url()


def get_test_api_url() -> str:
    """Get test API base URL."""
    config = get_config()
    return f"http://{config.api.host}:{config.api.port}"


# Test configuration instance
TEST_CONFIG = get_test_config()

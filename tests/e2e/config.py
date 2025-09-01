"""
Centralized configuration for E2E tests.
"""

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class TestEnvironmentConfig:
    """Centralized test environment configuration."""

    # Database
    database_url: str = (
        "postgresql+asyncpg://test_user:test_password@localhost:5434/devcycle_test"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_timeout: int = 30

    # Test execution
    test_timeout: int = 300
    parallel_workers: int = 4
    retry_attempts: int = 3

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    @classmethod
    def from_env(cls) -> "TestEnvironmentConfig":
        """Create configuration from environment variables."""
        return cls(
            database_url=os.getenv("TEST_DATABASE_URL", cls.database_url),
            api_host=os.getenv("TEST_API_HOST", cls.api_host),
            api_port=int(os.getenv("TEST_API_PORT", cls.api_port)),
            test_timeout=int(os.getenv("TEST_TIMEOUT", cls.test_timeout)),
            parallel_workers=int(
                os.getenv("TEST_PARALLEL_WORKERS", cls.parallel_workers)
            ),
        )


# Global test configuration
TEST_CONFIG = TestEnvironmentConfig.from_env()


def get_test_config(key: str, default: Any = None) -> Any:
    """Get test configuration value."""
    return getattr(TEST_CONFIG, key, default)


def get_test_database_url() -> str:
    """Get test database URL."""
    return TEST_CONFIG.database_url


def get_test_api_url() -> str:
    """Get test API base URL."""
    return f"http://{TEST_CONFIG.api_host}:{TEST_CONFIG.api_port}"

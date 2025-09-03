"""
Unified configuration management for DevCycle.

This module provides a single, environment-aware configuration system that
consolidates all configuration sources into a clean, validated approach.
"""

import os
import secrets
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Supported environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


def generate_secure_secret() -> str:
    """Generate a cryptographically secure secret key for development."""
    return secrets.token_urlsafe(32)


class LoggingConfig(BaseSettings):
    """Configuration for logging system."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    json_output: bool = Field(default=True, description="Output logs in JSON format")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    max_file_size: int = Field(
        default=10 * 1024 * 1024, description="Max log file size in bytes"
    )
    backup_count: int = Field(default=5, description="Number of backup log files")

    model_config = SettingsConfigDict(env_prefix="LOG_")


class DatabaseConfig(BaseSettings):
    """Configuration for database connection."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")
    database: str = Field(default="devcycle", description="Database name")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum overflow connections")
    echo: bool = Field(default=False, description="Echo SQL statements")

    model_config = SettingsConfigDict(env_prefix="DB_")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate database password is not empty in production."""
        if not v and os.getenv("ENVIRONMENT", "development") == "production":
            raise ValueError("Database password is required in production")
        return v

    @property
    def url(self) -> str:
        """Get database connection URL."""
        if self.password:
            return (
                f"postgresql://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
            )
        else:
            return (
                f"postgresql://{self.username}@{self.host}:{self.port}/{self.database}"
            )

    @property
    def async_url(self) -> str:
        """Get async database connection URL."""
        if self.password:
            return (
                f"postgresql+asyncpg://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
            )
        else:
            return (
                f"postgresql+asyncpg://{self.username}@"
                f"{self.host}:{self.port}/{self.database}"
            )


class SecurityConfig(BaseSettings):
    """Configuration for security settings."""

    secret_key: str = Field(
        default_factory=lambda: (
            generate_secure_secret() or "your-secret-key-here"
            if os.getenv("ENVIRONMENT", "development") == "development"
            else os.getenv("SECRET_KEY", "your-secret-key-here")
        ),
        description="Secret key for JWT tokens (required in production)",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    jwt_lifetime_seconds: int = Field(
        default=3600, description="JWT lifetime in seconds"
    )

    model_config = SettingsConfigDict(env_prefix="SECURITY_")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key meets security requirements."""
        if not v:
            raise ValueError("Secret key is required")

        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")

        # Check for common weak patterns
        weak_patterns = [
            "dev-secret-key-change-in-production",
            "secret",
            "password",
            "123456",
            "admin",
            "test",
        ]

        if any(pattern in v.lower() for pattern in weak_patterns):
            raise ValueError("Secret key contains weak patterns and is not secure")

        # In production, ensure it's not a development default
        if os.getenv("ENVIRONMENT", "development") == "production":
            if v == "dev-secret-key-change-in-production":
                raise ValueError("Secret key must be changed in production")

        return v


class APIConfig(BaseSettings):
    """Configuration for the API server."""

    host: str = Field(default="127.0.0.1", description="API server host")
    port: int = Field(default=8000, description="API server port")
    workers: int = Field(default=1, description="Number of API workers")
    reload: bool = Field(default=True, description="Enable auto-reload in development")
    cors_origins: List[str] = Field(
        default_factory=list, description="Allowed CORS origins"
    )
    cors_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_methods: List[str] = Field(
        default_factory=list, description="Allowed CORS methods"
    )
    cors_headers: List[str] = Field(
        default_factory=list, description="Allowed CORS headers"
    )
    cors_expose_headers: List[str] = Field(
        default_factory=list, description="Exposed CORS headers"
    )
    cors_max_age: int = Field(
        default=600, description="CORS preflight cache time in seconds"
    )
    request_timeout: int = Field(default=30, description="Request timeout in seconds")

    model_config = SettingsConfigDict(env_prefix="API_")

    def cors_origins_resolved(self, environment: str = "development") -> List[str]:
        """Get CORS origins based on environment."""
        if self.cors_origins:
            return self.cors_origins

        # Default environment-specific origins
        if environment == "development":
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ]
        elif environment == "staging":
            return [
                "https://staging.yourdomain.com",
                "https://staging-app.yourdomain.com",
            ]
        elif environment == "production":
            return [
                "https://yourdomain.com",
                "https://app.yourdomain.com",
            ]
        else:
            return []

    def cors_credentials_resolved(self, environment: str = "development") -> bool:
        """Get CORS credentials setting based on environment."""
        # More restrictive in production
        if environment == "production":
            return False
        return self.cors_credentials

    def cors_methods_resolved(self, environment: str = "development") -> List[str]:
        """Get CORS methods based on environment."""
        if self.cors_methods:
            return self.cors_methods

        if environment == "production":
            return ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        else:
            return ["*"]  # More permissive in development

    @property
    def cors_headers_resolved(self) -> List[str]:
        """Get CORS headers based on environment."""
        if self.cors_headers:
            return self.cors_headers

        return [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-CSRF-Token",
            "X-Requested-With",
        ]

    @property
    def cors_expose_headers_resolved(self) -> List[str]:
        """Get exposed CORS headers."""
        if self.cors_expose_headers:
            return self.cors_expose_headers

        return [
            "Content-Length",
            "Content-Type",
            "X-Total-Count",
        ]


class RedisConfig(BaseSettings):
    """Configuration for Redis connection."""

    host: str = Field(default="127.0.0.1", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis database number")
    max_connections: int = Field(default=10, description="Maximum Redis connections")
    socket_timeout: float = Field(default=5.0, description="Redis socket timeout")
    socket_connect_timeout: float = Field(
        default=5.0, description="Redis connection timeout"
    )
    retry_on_timeout: bool = Field(default=True, description="Retry on Redis timeout")
    health_check_interval: int = Field(
        default=30, description="Health check interval in seconds"
    )

    model_config = SettingsConfigDict(env_prefix="REDIS_")


class HuggingFaceConfig(BaseSettings):
    """Configuration for Hugging Face integration."""

    token: str = Field(default="", description="Hugging Face API token")
    org_name: str = Field(default="", description="Hugging Face organization name")

    model_config = SettingsConfigDict(env_prefix="HF_")


class AgentConfig(BaseSettings):
    """Configuration for AI agents."""

    # General agent settings
    max_execution_time: int = Field(
        default=300, description="Maximum execution time in seconds"
    )
    max_memory_usage: int = Field(
        default=1024, description="Maximum memory usage in MB"
    )
    enable_logging: bool = Field(default=True, description="Enable agent logging")
    enable_metrics: bool = Field(default=True, description="Enable agent metrics")

    # Model settings
    model_name: str = Field(default="gpt-3.5-turbo", description="Default model to use")
    temperature: float = Field(default=0.7, description="Model temperature")
    max_tokens: int = Field(default=1000, description="Maximum tokens to generate")

    # Retry settings
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(
        default=1.0, description="Delay between retries in seconds"
    )

    model_config = SettingsConfigDict(env_prefix="AGENT_")


class DockerConfig(BaseSettings):
    """Configuration for Docker services."""

    # PostgreSQL
    postgres_db: str = Field(default="devcycle", description="PostgreSQL database name")
    postgres_user: str = Field(default="postgres", description="PostgreSQL username")
    postgres_password: str = Field(
        default="devcycle123", description="PostgreSQL password"
    )
    postgres_port: int = Field(default=5432, description="PostgreSQL port")

    # pgAdmin
    pgadmin_email: str = Field(
        default="admin@devcycle.dev", description="pgAdmin email"
    )
    pgadmin_password: str = Field(default="admin123", description="pgAdmin password")

    # Default users (development only)
    default_admin_username: str = Field(
        default="admin", description="Default admin username"
    )
    default_admin_password: str = Field(
        default="admin123", description="Default admin password"
    )
    default_user_username: str = Field(
        default="user", description="Default user username"
    )
    default_user_password: str = Field(
        default="user123", description="Default user password"
    )

    model_config = SettingsConfigDict(env_prefix="DOCKER_")


class TestConfig(BaseSettings):
    """Configuration for testing environment."""

    database_url: str = Field(
        default=(
            "postgresql+asyncpg://test_user:test_password@localhost:5434/devcycle_test"
        ),
        description="Test database URL",
    )
    api_host: str = Field(default="127.0.0.1", description="Test API host")
    api_port: int = Field(default=8000, description="Test API port")
    test_timeout: int = Field(default=300, description="Test timeout in seconds")
    parallel_workers: int = Field(default=4, description="Parallel test workers")
    retry_attempts: int = Field(default=3, description="Test retry attempts")

    model_config = SettingsConfigDict(env_prefix="TEST_")


class DevCycleConfig(BaseSettings):
    """Main unified configuration class for DevCycle."""

    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Current environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # Component configurations
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    huggingface: HuggingFaceConfig = Field(default_factory=HuggingFaceConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    test: TestConfig = Field(default_factory=TestConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v: Union[str, Environment]) -> Environment:
        """Validate and convert environment string to enum."""
        if isinstance(v, Environment):
            return v
        if isinstance(v, str):
            try:
                return Environment(v.lower())
            except ValueError:
                raise ValueError(
                    f"Invalid environment: {v}. "
                    f"Must be one of: {[e.value for e in Environment]}"
                )
        raise ValueError(f"Invalid environment type: {type(v)}")

    @field_validator("debug")
    @classmethod
    def validate_debug(cls, v: bool, info: Any) -> bool:
        """Ensure debug is False in production."""
        if v and info.data.get("environment") == Environment.PRODUCTION:
            raise ValueError("Debug mode cannot be enabled in production")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization validation."""
        super().model_post_init(__context)
        self._validate_production_cors_config()

    @property
    def cors_origins_resolved(self) -> List[str]:
        """Get resolved CORS origins for this environment."""
        return self.api.cors_origins_resolved(self.environment.value)

    @property
    def cors_credentials_resolved(self) -> bool:
        """Get resolved CORS credentials for this environment."""
        return self.api.cors_credentials_resolved(self.environment.value)

    @property
    def cors_methods_resolved(self) -> List[str]:
        """Get resolved CORS methods for this environment."""
        return self.api.cors_methods_resolved(self.environment.value)

    @property
    def cors_headers_resolved(self) -> List[str]:
        """Get resolved CORS headers for this environment."""
        return self.api.cors_headers_resolved

    @property
    def cors_expose_headers_resolved(self) -> List[str]:
        """Get resolved exposed CORS headers for this environment."""
        return self.api.cors_expose_headers_resolved

    def _validate_production_cors_config(self) -> None:
        """Validate production CORS configuration security."""
        if self.environment == Environment.PRODUCTION:
            # Only validate explicitly configured CORS origins, not resolved defaults
            cors_origins = self.api.cors_origins

            # If no origins are explicitly configured, that's an error in production
            if not cors_origins:
                raise ValueError(
                    "Production environment must specify allowed CORS origins. "
                    "Set API_CORS_ORIGINS environment variable."
                )

            # Ensure CORS is properly restricted
            if "*" in cors_origins:
                raise ValueError(
                    "Production environment cannot allow all CORS origins (*). "
                    "Please specify allowed origins explicitly."
                )

            # Validate CORS origins are HTTPS
            for origin in cors_origins:
                if not origin.startswith("https://"):
                    raise ValueError(
                        f"Production CORS origin must use HTTPS: {origin}. "
                        "All production origins must be secure."
                    )

            # Validate no localhost origins in production
            for origin in cors_origins:
                if "localhost" in origin or "127.0.0.1" in origin:
                    raise ValueError(
                        f"Production environment cannot allow localhost origins: "
                        f"{origin}. Use production domain names only."
                    )

            # Validate credentials setting - use the actual configured value
            if self.api.cors_credentials:
                raise ValueError(
                    "Production environment should not allow CORS credentials. "
                    "Set API_CORS_CREDENTIALS=false for production."
                )

    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent configuration dictionary or None if not found
        """
        # For now, return the default agent config
        # In the future, this could be extended to support agent-specific configs
        return self.agent.model_dump() if self.agent else None

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING

    def get_database_url(self) -> str:
        """Get the appropriate database URL for the current environment."""
        if self.is_testing():
            return self.test.database_url
        return self.database.url

    def get_async_database_url(self) -> str:
        """Get the appropriate async database URL for the current environment."""
        if self.is_testing():
            return self.test.database_url
        return self.database.async_url


# Global configuration instance
_config: Optional[DevCycleConfig] = None


def get_config() -> DevCycleConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = DevCycleConfig()
    return _config


def set_config(config: DevCycleConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def reload_config() -> DevCycleConfig:
    """Reload configuration from environment variables."""
    global _config
    _config = DevCycleConfig()
    return _config


def get_environment() -> Environment:
    """Get the current environment."""
    return get_config().environment


def is_development() -> bool:
    """Check if running in development environment."""
    return get_config().is_development()


def is_production() -> bool:
    """Check if running in production environment."""
    return get_config().is_production()


def is_testing() -> bool:
    """Check if running in testing environment."""
    return get_config().is_testing()

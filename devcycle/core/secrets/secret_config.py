"""
Enhanced configuration system with GCP Secret Manager integration.

This module extends the base configuration to automatically retrieve
secrets from GCP Secret Manager while maintaining backward compatibility
with environment variables for development.
"""

import os
import secrets
from typing import Any, Dict, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from devcycle.core.config.settings import Environment, generate_secure_secret
from devcycle.core.secrets.gcp_secret_manager import get_secret_client


class SecretAwareSecurityConfig(BaseSettings):
    """
    Security configuration with GCP Secret Manager integration.

    This configuration automatically retrieves secrets from GCP Secret Manager
    in production while falling back to environment variables in development.
    """

    secret_key: str = Field(
        default_factory=lambda: SecretAwareSecurityConfig._get_secret_key(),
        description="Secret key for JWT tokens (retrieved from GCP Secret Manager in production)",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    jwt_lifetime_seconds: int = Field(
        default=3600, description="JWT lifetime in seconds"
    )

    model_config = SettingsConfigDict(env_prefix="SECURITY_", env_ignore_empty=True)

    def __init__(self, **data):
        """Custom initialization to handle secret_key from GCP or environment."""
        # Get secret_key from GCP or environment before calling super().__init__
        if "secret_key" not in data:
            data["secret_key"] = self._get_secret_key()
        super().__init__(**data)

    @staticmethod
    def _get_secret_key() -> str:
        """Get secret key from GCP Secret Manager or environment."""
        environment = os.getenv("ENVIRONMENT", "development")

        # In production or testing, try GCP Secret Manager first
        if environment in ["production", "testing"]:
            secret_client = get_secret_client()
            secret_value = secret_client.get_secret(
                "jwt-secret-key",
                environment="prod" if environment == "production" else "test",
            )
            if secret_value:
                return secret_value

        # Fallback to environment variable
        env_secret = os.getenv("SECRET_KEY")
        if env_secret:
            return env_secret

        # Development fallback
        if environment == "development":
            return generate_secure_secret()

        # Production fallback (should not reach here)
        raise ValueError(
            "SECRET_KEY must be set in production environment. "
            "Either set SECRET_KEY environment variable or configure GCP Secret Manager."
        )

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
            "your-secret-key-here",
        ]

        if any(pattern in v.lower() for pattern in weak_patterns):
            raise ValueError("Secret key contains weak patterns and is not secure")

        # In production, ensure it's not a development default
        if os.getenv("ENVIRONMENT", "development") == "production":
            if v in ["dev-secret-key-change-in-production", "your-secret-key-here"]:
                raise ValueError("Secret key must be changed in production")

        return v


class SecretAwareDatabaseConfig(BaseSettings):
    """
    Database configuration with GCP Secret Manager integration.
    """

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(
        default_factory=lambda: SecretAwareDatabaseConfig._get_db_password(),
        description="Database password (retrieved from GCP Secret Manager in production)",
    )
    database: str = Field(default="devcycle", description="Database name")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum overflow connections")
    echo: bool = Field(default=False, description="Echo SQL statements")

    model_config = SettingsConfigDict(env_prefix="DB_", env_ignore_empty=True)

    def __init__(self, **data):
        """Custom initialization to handle password from GCP or environment."""
        # Get password from GCP or environment before calling super().__init__
        if "password" not in data:
            data["password"] = self._get_db_password()
        super().__init__(**data)

    @staticmethod
    def _get_db_password() -> str:
        """Get database password from GCP Secret Manager or environment."""
        environment = os.getenv("ENVIRONMENT", "development")
        print(f"DEBUG: _get_db_password called with environment={environment}")

        # In production or testing, try GCP Secret Manager first
        if environment in ["production", "testing"]:
            print(f"DEBUG: In {environment} mode, calling GCP client")
            secret_client = get_secret_client()
            secret_value = secret_client.get_secret(
                "database-password",
                environment="prod" if environment == "production" else "test",
            )
            print(f"DEBUG: GCP secret value: {secret_value}")
            if secret_value:
                return secret_value

        # Fallback to environment variable
        env_password = os.getenv("DB_PASSWORD")
        if env_password:
            return env_password

        # Development fallback
        if environment == "development":
            return "devcycle123"  # Default dev password

        # Production fallback (should not reach here)
        raise ValueError(
            "DB_PASSWORD must be set in production environment. "
            "Either set DB_PASSWORD environment variable or configure GCP Secret Manager."
        )

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


class SecretAwareRedisConfig(BaseSettings):
    """
    Redis configuration with GCP Secret Manager integration.
    """

    host: str = Field(default="127.0.0.1", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(
        default_factory=lambda: SecretAwareRedisConfig._get_redis_password(),
        description="Redis password (retrieved from GCP Secret Manager in production)",
    )
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

    model_config = SettingsConfigDict(env_prefix="REDIS_", env_ignore_empty=True)

    def __init__(self, **data):
        """Custom initialization to handle password from GCP or environment."""
        # Get password from GCP or environment before calling super().__init__
        if "password" not in data:
            data["password"] = self._get_redis_password()
        super().__init__(**data)

    @staticmethod
    def _get_redis_password() -> Optional[str]:
        """Get Redis password from GCP Secret Manager or environment."""
        environment = os.getenv("ENVIRONMENT", "development")

        # In production or testing, try GCP Secret Manager first
        if environment in ["production", "testing"]:
            secret_client = get_secret_client()
            secret_value = secret_client.get_secret(
                "redis-password",
                environment="prod" if environment == "production" else "test",
            )
            if secret_value:
                return secret_value

        # Fallback to environment variable
        env_password = os.getenv("REDIS_PASSWORD")
        if env_password:
            return env_password

        # Development fallback (no password)
        return None


class SecretAwareHuggingFaceConfig(BaseSettings):
    """
    Hugging Face configuration with GCP Secret Manager integration.
    """

    token: str = Field(
        default_factory=lambda: SecretAwareHuggingFaceConfig._get_hf_token(),
        description="Hugging Face API token (retrieved from GCP Secret Manager in production)",
    )
    org_name: str = Field(default="", description="Hugging Face organization name")

    model_config = SettingsConfigDict(env_prefix="HF_", env_ignore_empty=True)

    def __init__(self, **data):
        """Custom initialization to handle token from GCP or environment."""
        # Get token from GCP or environment before calling super().__init__
        if "token" not in data:
            data["token"] = self._get_hf_token()
        super().__init__(**data)

    @staticmethod
    def _get_hf_token() -> str:
        """Get Hugging Face token from GCP Secret Manager or environment."""
        environment = os.getenv("ENVIRONMENT", "development")

        # In production or testing, try GCP Secret Manager first
        if environment in ["production", "testing"]:
            secret_client = get_secret_client()
            secret_value = secret_client.get_secret(
                "huggingface-token",
                environment="prod" if environment == "production" else "test",
            )
            if secret_value:
                return secret_value

        # Fallback to environment variable
        env_token = os.getenv("HF_TOKEN")
        if env_token:
            return env_token

        # Development fallback (empty token)
        return ""


def get_production_secrets() -> Dict[str, str]:
    """
    Get all production secrets from GCP Secret Manager.

    Returns:
        Dictionary of secret names and values
    """
    secret_client = get_secret_client()
    secrets_dict = {}

    # List of secrets to retrieve
    secret_ids = [
        "jwt-secret-key",
        "database-password",
        "redis-password",
        "huggingface-token",
    ]

    for secret_id in secret_ids:
        secret_value = secret_client.get_secret(secret_id, environment="prod")
        if secret_value:
            secrets_dict[secret_id] = secret_value

    return secrets_dict


def validate_production_secrets() -> bool:
    """
    Validate that all required production secrets are available.

    Returns:
        True if all secrets are available, False otherwise
    """
    if os.getenv("ENVIRONMENT", "development") != "production":
        return True

    secret_client = get_secret_client()
    required_secrets = [
        "jwt-secret-key",
        "database-password",
    ]

    missing_secrets = []
    for secret_id in required_secrets:
        secret_value = secret_client.get_secret(secret_id, environment="prod")
        if not secret_value:
            missing_secrets.append(secret_id)

    if missing_secrets:
        print(f"ERROR: Missing required production secrets: {missing_secrets}")
        print(
            "Please configure these secrets in GCP Secret Manager or set environment variables."
        )
        return False

    return True

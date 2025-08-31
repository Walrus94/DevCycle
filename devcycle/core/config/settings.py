"""
Configuration settings for DevCycle.

This module contains all configuration classes and settings management
for the DevCycle system.
"""

from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


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

    model_config = {"env_prefix": "LOG_"}


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

    model_config = {"env_prefix": "DB_"}


class HuggingFaceConfig(BaseSettings):
    """Configuration for Hugging Face integration."""

    token: str = Field(default="", description="Hugging Face API token")
    org_name: str = Field(default="", description="Hugging Face organization name")

    model_config = {"env_prefix": "HF_"}


class APIConfig(BaseSettings):
    """Configuration for the API server."""

    host: str = Field(default="127.0.0.1", description="API server host")
    port: int = Field(default=8000, description="API server port")
    workers: int = Field(default=1, description="Number of API workers")
    reload: bool = Field(default=True, description="Enable auto-reload in development")
    cors_origins: List[str] = Field(default=["*"], description="Allowed CORS origins")
    cors_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_methods: List[str] = Field(default=["*"], description="Allowed CORS methods")
    cors_headers: List[str] = Field(default=["*"], description="Allowed CORS headers")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")

    model_config = {"env_prefix": "API_"}


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

    model_config = {"env_prefix": "REDIS_"}


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

    model_config = {"env_prefix": "AGENT_"}


class DevCycleConfig(BaseSettings):
    """Main configuration class for DevCycle."""

    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Component configurations
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    huggingface: HuggingFaceConfig = Field(default_factory=HuggingFaceConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

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

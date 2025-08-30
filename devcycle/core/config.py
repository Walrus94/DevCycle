"""
Configuration management for DevCycle system.

This module provides centralized configuration management using Pydantic settings
for type safety and environment variable support.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class HuggingFaceConfig(BaseSettings):
    """Configuration for Hugging Face integration."""

    api_token: Optional[str] = Field(default=None, description="Hugging Face API token")
    hub_url: str = Field(
        default="https://huggingface.co", description="Hugging Face Hub URL"
    )
    spaces_url: str = Field(
        default="https://huggingface.co/spaces", description="Hugging Face Spaces URL"
    )
    cache_dir: Path = Field(
        default=Path.home() / ".cache" / "huggingface", description="Cache directory"
    )

    model_config = SettingsConfigDict(env_prefix="HF_")


class AgentConfig(BaseSettings):
    """Configuration for AI agents."""

    max_concurrent_agents: int = Field(
        default=5, description="Maximum concurrent agents"
    )
    agent_timeout: int = Field(
        default=300, description="Agent execution timeout in seconds"
    )
    retry_attempts: int = Field(
        default=3, description="Number of retry attempts for failed operations"
    )

    # Agent-specific configurations
    requirements_agent: Dict[str, Any] = Field(default_factory=dict)
    codegen_agent: Dict[str, Any] = Field(default_factory=dict)
    testing_agent: Dict[str, Any] = Field(default_factory=dict)
    deployment_agent: Dict[str, Any] = Field(default_factory=dict)

    model_config = SettingsConfigDict(env_prefix="AGENT_")


class LoggingConfig(BaseSettings):
    """Configuration for logging system."""

    level: str = Field(default="INFO", description="Logging level")
    file_path: Optional[Path] = Field(default=None, description="Log file path")
    json_output: bool = Field(
        default=True, description="Output JSON logs for production/Kibana"
    )

    model_config = SettingsConfigDict(env_prefix="LOG_")


class DatabaseConfig(BaseSettings):
    """Configuration for database connections."""

    url: str = Field(
        default="sqlite:///./devcycle.db", description="Database connection URL"
    )
    echo: bool = Field(default=False, description="Echo SQL queries")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Maximum connection overflow")

    model_config = SettingsConfigDict(env_prefix="DB_")


class DevCycleConfig(BaseSettings):
    """Main configuration class for DevCycle system."""

    # Basic project info
    project_name: str = Field(default="DevCycle", description="Project name")
    version: str = Field(default="0.1.0", description="Project version")
    environment: str = Field(
        default="development", description="Environment (dev/staging/prod)"
    )
    debug: bool = Field(default=False, description="Debug mode")

    # Paths
    base_dir: Path = Field(default=Path.cwd(), description="Base project directory")
    data_dir: Path = Field(default=Path.cwd() / "data", description="Data directory")
    logs_dir: Path = Field(default=Path.cwd() / "logs", description="Logs directory")
    temp_dir: Path = Field(
        default=Path.cwd() / "tmp", description="Temporary files directory"
    )

    # Sub-configurations
    huggingface: HuggingFaceConfig = Field(default_factory=HuggingFaceConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    # API configuration
    api_host: str = Field(default="127.0.0.1", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=1, description="Number of API workers")

    # Security
    secret_key: str = Field(
        default="devcycle-secret-key-change-in-production",
        description="Secret key for security",
    )
    allowed_hosts: List[str] = Field(
        default=["127.0.0.1", "localhost"], description="Allowed hosts"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @field_validator("environment")  # type: ignore[misc]
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "staging", "production", "testing"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v

    @field_validator(
        "base_dir", "data_dir", "logs_dir", "temp_dir"
    )  # type: ignore[misc]
    @classmethod
    def ensure_directories_exist(cls, v: Path) -> Path:
        """Ensure directories exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for a specific agent."""
        agent_configs = {
            "requirements": self.agent.requirements_agent,
            "codegen": self.agent.codegen_agent,
            "testing": self.agent.testing_agent,
            "deployment": self.agent.deployment_agent,
        }
        return agent_configs.get(agent_name, {})

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def get_log_file_path(self) -> Optional[Path]:
        """Get the log file path, creating logs directory if needed."""
        if self.logging.file_path:
            return self.logging.file_path

        if self.logs_dir:
            return self.logs_dir / "devcycle.log"

        return None

    def should_use_json_logs(self) -> bool:
        """Check if JSON logging should be used."""
        return self.logging.json_output or self.is_production()


# Global configuration instance
config = DevCycleConfig()


def get_config() -> DevCycleConfig:
    """Get the global configuration instance."""
    return config


def reload_config() -> DevCycleConfig:
    """Reload configuration from environment and files."""
    global config
    config = DevCycleConfig()
    return config

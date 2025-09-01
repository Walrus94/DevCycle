"""
Configuration loader for environment-specific settings.

This module provides utilities to load configuration from environment-specific
files and merge them with environment variables.
"""

import os
from pathlib import Path
from typing import Dict, Optional

from pydantic_settings import BaseSettings


def load_env_file(env_file_path: Path) -> Dict[str, str]:
    """
    Load environment variables from a .env file.

    Args:
        env_file_path: Path to the .env file

    Returns:
        Dictionary of environment variables
    """
    env_vars: Dict[str, str] = {}

    if not env_file_path.exists():
        return env_vars

    with open(env_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse key=value pairs
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                env_vars[key] = value

    return env_vars


def get_environment_config_file(environment: str) -> Path:
    """
    Get the configuration file path for a specific environment.

    Args:
        environment: Environment name (development, testing, production, staging)

    Returns:
        Path to the environment-specific configuration file
    """
    project_root = Path(__file__).parent.parent.parent.parent
    config_dir = project_root / "config"
    return config_dir / f"{environment}.env"


def load_environment_config(environment: str) -> Dict[str, str]:
    """
    Load configuration for a specific environment.

    Args:
        environment: Environment name

    Returns:
        Dictionary of environment variables
    """
    env_file = get_environment_config_file(environment)
    return load_env_file(env_file)


def setup_environment_config(environment: str) -> None:
    """
    Set up environment variables from environment-specific config file.

    Args:
        environment: Environment name
    """
    env_vars = load_environment_config(environment)

    # Set environment variables (only if not already set)
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value


def get_environment_from_env() -> str:
    """
    Get the current environment from environment variables.

    Returns:
        Environment name, defaults to 'development'
    """
    return os.getenv("ENVIRONMENT", "development")


def create_config_with_environment(environment: Optional[str] = None) -> BaseSettings:
    """
    Create a configuration instance with environment-specific settings.

    Args:
        environment: Environment name, if None will be determined from ENV

    Returns:
        Configured settings instance
    """
    from .settings import DevCycleConfig

    if environment is None:
        environment = get_environment_from_env()

    # Load environment-specific configuration
    setup_environment_config(environment)

    # Create config instance
    return DevCycleConfig()


def validate_environment_config(environment: str) -> bool:
    """
    Validate that an environment configuration file exists and is readable.

    Args:
        environment: Environment name

    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        env_file = get_environment_config_file(environment)
        if not env_file.exists():
            return False

        # Try to load the configuration
        load_environment_config(environment)
        return True
    except Exception:
        return False


def list_available_environments() -> list[str]:
    """
    List all available environment configurations.

    Returns:
        List of environment names that have configuration files
    """
    project_root = Path(__file__).parent.parent.parent.parent
    config_dir = project_root / "config"

    if not config_dir.exists():
        return []

    environments = []
    for env_file in config_dir.glob("*.env"):
        env_name = env_file.stem
        if validate_environment_config(env_name):
            environments.append(env_name)

    return sorted(environments)

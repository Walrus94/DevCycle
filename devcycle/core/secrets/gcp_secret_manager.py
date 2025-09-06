"""
GCP Secret Manager integration for secure secret management.

This module provides a client for Google Cloud Secret Manager that supports:
- Secret retrieval with caching
- Automatic rotation support
- Environment-specific secret management
- Fallback to environment variables for development
"""

import json
import logging
import os
from typing import Any, Dict, Optional, Union

from ..cache.redis_cache import get_cache

try:
    from google.api_core import exceptions as gcp_exceptions
    from google.cloud import secretmanager
    from google.cloud.secretmanager import SecretManagerServiceClient

    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False
    gcp_exceptions = None
    secretmanager = None
    SecretManagerServiceClient = None

from devcycle.core.config import get_config

from ..cache.redis_cache import RedisCache

logger = logging.getLogger(__name__)


class GCPSecretManagerClient:
    """
    Client for Google Cloud Secret Manager with rotation support.

    Features:
    - Automatic secret retrieval from GCP Secret Manager
    - Caching for performance
    - Environment-specific secret naming
    - Fallback to environment variables for development
    - Support for JSON secrets
    """

    cache: Optional[RedisCache]
    client: Optional[SecretManagerServiceClient]

    def __init__(
        self,
        project_id: Optional[str] = None,
        cache_ttl: int = 300,  # 5 minutes cache
        enable_caching: bool = True,
    ):
        """
        Initialize the GCP Secret Manager client.

        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            cache_ttl: Cache TTL in seconds
            enable_caching: Whether to enable Redis caching
        """
        self.project_id = project_id or self._get_project_id()
        self.cache_ttl = cache_ttl
        self.enable_caching = enable_caching

        # Initialize Redis cache for distributed caching
        if self.enable_caching:
            self.cache = get_cache("devcycle:secrets:")
        else:
            self.cache = None

        # Initialize GCP client if available
        if GCP_AVAILABLE and self.project_id:
            try:
                self.client = secretmanager.SecretManagerServiceClient()
                self.gcp_enabled = True
                logger.info(
                    f"GCP Secret Manager initialized for project: {self.project_id}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize GCP Secret Manager: {e}")
                self.client = None
                self.gcp_enabled = False
        else:
            self.client = None
            self.gcp_enabled = False
            if not GCP_AVAILABLE:
                logger.warning(
                    "GCP Secret Manager not available. "
                    "Install google-cloud-secret-manager"
                )
            if not self.project_id:
                logger.warning(
                    "GCP project ID not found. "
                    "Set GOOGLE_CLOUD_PROJECT environment variable"
                )

    def _get_project_id(self) -> Optional[str]:
        """Get GCP project ID from environment or metadata service."""
        # Try environment variable first
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if project_id:
            return project_id

        # Try GCP metadata service
        if GCP_AVAILABLE:
            try:
                import requests

                response = requests.get(
                    "http://metadata.google.internal/computeMetadata/v1/"
                    "project/project-id",
                    headers={"Metadata-Flavor": "Google"},
                    timeout=2,
                )
                if response.status_code == 200:
                    return str(response.text.strip())
            except Exception as e:
                logger.debug(f"Failed to get project ID from metadata service: {e}")

        return None

    def _get_secret_name(
        self, secret_id: str, environment: Optional[str] = None
    ) -> str:
        """
        Generate secret name with environment prefix.

        Args:
            secret_id: Base secret identifier
            environment: Environment name (dev, staging, prod)

        Returns:
            Full secret name for GCP Secret Manager
        """
        if not environment:
            config = get_config()
            environment = config.environment.value

        # Use environment-specific naming
        return (
            f"projects/{self.project_id}/secrets/"
            f"{environment}-{secret_id}/versions/latest"
        )

    def _get_cache_key(self, secret_name: str) -> str:
        """Get Redis cache key for secret."""
        return f"{secret_name}"

    def _cache_secret(self, secret_name: str, value: str) -> None:
        """Cache secret value in Redis."""
        if self.cache:
            cache_key = self._get_cache_key(secret_name)
            self.cache.set(cache_key, value, ttl=self.cache_ttl)

    def _get_cached_secret(self, secret_name: str) -> Optional[str]:
        """Get cached secret value from Redis."""
        if self.cache:
            cache_key = self._get_cache_key(secret_name)
            return self.cache.get(cache_key)
        return None

    def _clear_cached_secret(self, secret_name: str) -> None:
        """Clear cached secret from Redis."""
        if self.cache:
            cache_key = self._get_cache_key(secret_name)
            self.cache.delete(cache_key)

    def clear_all_caches(self) -> int:
        """
        Clear all cached secrets from Redis.

        Returns:
            Number of cache entries cleared
        """
        if self.cache:
            return self.cache.clear_pattern("*")
        return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if self.cache:
            return self.cache.get_stats()
        return {"total_keys": 0, "redis_connected": False, "caching_enabled": False}

    def get_secret(
        self,
        secret_id: str,
        environment: Optional[str] = None,
        fallback_env_var: Optional[str] = None,
        parse_json: bool = False,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Retrieve a secret from GCP Secret Manager.

        Args:
            secret_id: Secret identifier
            environment: Environment name
            fallback_env_var: Environment variable to fallback to
            parse_json: Whether to parse the secret as JSON

        Returns:
            Secret value or None if not found
        """
        secret_name = self._get_secret_name(secret_id, environment)

        # Check cache first
        cached_value = self._get_cached_secret(secret_name)
        if cached_value is not None:
            logger.debug(f"Retrieved cached secret: {secret_id}")
            return self._parse_secret_value(cached_value, parse_json)

        # Try GCP Secret Manager
        if self.gcp_enabled and self.client:
            try:
                response = self.client.access_secret_version(
                    request={"name": secret_name}
                )
                secret_value = response.payload.data.decode("UTF-8")
                self._cache_secret(secret_name, secret_value)
                logger.info(f"Retrieved secret from GCP: {secret_id}")
                return self._parse_secret_value(secret_value, parse_json)
            except gcp_exceptions.NotFound:
                logger.warning(f"Secret not found in GCP: {secret_id}")
            except Exception as e:
                logger.error(f"Error retrieving secret from GCP: {e}")

        # Fallback to environment variable
        if fallback_env_var:
            env_value = os.getenv(fallback_env_var)
            if env_value:
                logger.info(f"Using fallback environment variable: {fallback_env_var}")
                return self._parse_secret_value(env_value, parse_json)

        # Try direct environment variable with secret_id
        env_value = os.getenv(secret_id.upper().replace("-", "_"))
        if env_value:
            logger.info(
                f"Using direct environment variable: "
                f"{secret_id.upper().replace('-', '_')}"
            )
            return self._parse_secret_value(env_value, parse_json)

        logger.error(f"Secret not found: {secret_id}")
        return None

    def _parse_secret_value(
        self, value: str, parse_json: bool
    ) -> Union[str, Dict[str, Any]]:
        """Parse secret value as JSON if requested."""
        if parse_json:
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    logger.warning("JSON secret is not a dict, returning as string")
                    return value
            except json.JSONDecodeError:
                logger.warning("Failed to parse secret as JSON, returning as string")
                return value
        return value

    def create_secret(
        self, secret_id: str, secret_value: str, environment: Optional[str] = None
    ) -> bool:
        """
        Create a new secret in GCP Secret Manager.

        Args:
            secret_id: Secret identifier
            secret_value: Secret value
            environment: Environment name

        Returns:
            True if successful, False otherwise
        """
        if not self.gcp_enabled or not self.client:
            logger.error("GCP Secret Manager not available")
            return False

        try:
            secret_name = self._get_secret_name(secret_id, environment)
            parent = f"projects/{self.project_id}"

            # Create secret if it doesn't exist
            try:
                self.client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": f"{environment or 'dev'}-{secret_id}",
                        "secret": {"replication": {"automatic": {}}},
                    }
                )
                logger.info(f"Created secret: {secret_id}")
            except gcp_exceptions.AlreadyExists:
                logger.debug(f"Secret already exists: {secret_id}")

            # Add secret version
            self.client.add_secret_version(
                request={
                    "parent": secret_name.replace("/versions/latest", ""),
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )

            # Clear cache
            self._clear_cached_secret(secret_name)

            logger.info(f"Updated secret: {secret_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating/updating secret: {e}")
            return False

    def rotate_secret(
        self, secret_id: str, new_value: str, environment: Optional[str] = None
    ) -> bool:
        """
        Rotate a secret by adding a new version.

        Args:
            secret_id: Secret identifier
            new_value: New secret value
            environment: Environment name

        Returns:
            True if successful, False otherwise
        """
        return self.create_secret(secret_id, new_value, environment)

    def list_secrets(self, environment: Optional[str] = None) -> list:
        """
        List all secrets for the given environment.

        Args:
            environment: Environment name

        Returns:
            List of secret names
        """
        if not self.gcp_enabled or not self.client:
            return []

        try:
            parent = f"projects/{self.project_id}"
            prefix = f"{environment or 'dev'}-" if environment else ""

            secrets = []
            for secret in self.client.list_secrets(request={"parent": parent}):
                secret_name = secret.name.split("/")[-1]
                if secret_name.startswith(prefix):
                    secrets.append(secret_name[len(prefix) :])

            return secrets
        except Exception as e:
            logger.error(f"Error listing secrets: {e}")
            return []

    def delete_secret(self, secret_id: str, environment: Optional[str] = None) -> bool:
        """
        Delete a secret from GCP Secret Manager.

        Args:
            secret_id: Secret identifier
            environment: Environment name

        Returns:
            True if successful, False otherwise
        """
        if not self.gcp_enabled or not self.client:
            return False

        try:
            secret_name = (
                f"projects/{self.project_id}/secrets/{environment or 'dev'}-{secret_id}"
            )
            self.client.delete_secret(request={"name": secret_name})

            # Clear cache
            self._clear_cached_secret(secret_name)

            logger.info(f"Deleted secret: {secret_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting secret: {e}")
            return False


# Global client instance
_secret_client: Optional[GCPSecretManagerClient] = None


def get_secret_client() -> GCPSecretManagerClient:
    """Get the global secret manager client instance."""
    global _secret_client
    if _secret_client is None:
        _secret_client = GCPSecretManagerClient()
    return _secret_client


def get_secret(
    secret_id: str,
    environment: Optional[str] = None,
    fallback_env_var: Optional[str] = None,
    parse_json: bool = False,
) -> Optional[Union[str, Dict[str, Any]]]:
    """Get a secret from GCP Secret Manager or environment fallback.

    Args:
        secret_id: Secret identifier
        environment: Environment name
        fallback_env_var: Environment variable to fallback to
        parse_json: Whether to parse the secret as JSON

    Returns:
        Secret value or None if not found
    """
    client = get_secret_client()
    return client.get_secret(secret_id, environment, fallback_env_var, parse_json)


def create_secret(
    secret_id: str, secret_value: str, environment: Optional[str] = None
) -> bool:
    """Create a secret in GCP Secret Manager.

    Args:
        secret_id: Secret identifier
        secret_value: Secret value
        environment: Environment name

    Returns:
        True if successful, False otherwise
    """
    client = get_secret_client()
    return client.create_secret(secret_id, secret_value, environment)


def rotate_secret(
    secret_id: str, new_value: str, environment: Optional[str] = None
) -> bool:
    """Rotate a secret in GCP Secret Manager.

    Args:
        secret_id: Secret identifier
        new_value: New secret value
        environment: Environment name

    Returns:
        True if successful, False otherwise
    """
    client = get_secret_client()
    return client.rotate_secret(secret_id, new_value, environment)

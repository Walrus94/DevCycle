"""
Unit tests for GCP Secret Manager integration.

These tests focus on the core functionality of the GCPSecretManagerClient
with mocked dependencies to ensure fast execution and isolation.
"""

import os
from unittest.mock import Mock, patch

import pytest
from google.api_core import exceptions as gcp_exceptions

from devcycle.core.secrets.gcp_secret_manager import (
    GCPSecretManagerClient,
    create_secret,
    get_secret,
    get_secret_client,
    rotate_secret,
)


@pytest.mark.unit
class TestGCPSecretManagerClient:
    """Test the GCPSecretManagerClient class."""

    def test_init_with_project_id(self):
        """Test client initialization with explicit project ID."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")

            assert client.project_id == "test-project"
            assert client.gcp_enabled is True
            assert client.client == mock_client

    def test_init_without_project_id(self):
        """Test client initialization without project ID."""
        with (
            patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm,
            patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "env-project"}),
        ):

            mock_client = Mock()
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient()

            assert client.project_id == "env-project"
            assert client.gcp_enabled is True

    def test_init_gcp_client_failure(self):
        """Test client initialization when GCP client creation fails."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_sm.SecretManagerServiceClient.side_effect = Exception(
                "GCP client error"
            )

            client = GCPSecretManagerClient(project_id="test-project")

            assert client.gcp_enabled is False
            assert client.client is None

    def test_get_project_id_from_metadata(self):
        """Test project ID retrieval from GCP metadata service."""
        with (
            patch("requests.get") as mock_requests_get,
            patch.dict(os.environ, {}, clear=True),
        ):  # Clear environment variables
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "metadata-project"
            mock_requests_get.return_value = mock_response

            # Create client without project_id to trigger metadata lookup
            client = GCPSecretManagerClient(project_id=None)
            project_id = client._get_project_id()

            assert project_id == "metadata-project"
            # Should be called at least once (may be called during initialization too)
            assert mock_requests_get.call_count >= 1

    def test_get_secret_name(self):
        """Test secret name generation."""
        client = GCPSecretManagerClient(project_id="test-project")

        # Test with explicit environment
        secret_name = client._get_secret_name("jwt-secret-key", "prod")
        assert (
            secret_name
            == "projects/test-project/secrets/prod-jwt-secret-key/versions/latest"
        )

        # Test with default environment
        with patch(
            "devcycle.core.secrets.gcp_secret_manager.get_config"
        ) as mock_config:
            mock_config.return_value.environment.value = "staging"
            secret_name = client._get_secret_name("jwt-secret-key")
            assert (
                secret_name == "projects/test-project/secrets/"
                "staging-jwt-secret-key/versions/latest"
            )

    def test_cache_operations(self):
        """Test secret caching functionality with Redis."""
        with patch(
            "devcycle.core.secrets.gcp_secret_manager.get_cache"
        ) as mock_get_cache:
            mock_cache = Mock()
            mock_get_cache.return_value = mock_cache

            client = GCPSecretManagerClient(project_id="test-project", cache_ttl=300)

            # Test caching
            client._cache_secret("test-secret", "test-value")
            mock_cache.set.assert_called_once_with("test-secret", "test-value", ttl=300)

            # Test cache retrieval
            mock_cache.get.return_value = "test-value"
            result = client._get_cached_secret("test-secret")
            assert result == "test-value"
            mock_cache.get.assert_called_once_with("test-secret")

            # Test cache clearing
            client._clear_cached_secret("test-secret")
            mock_cache.delete.assert_called_once_with("test-secret")

    def test_get_secret_from_gcp(self):
        """Test secret retrieval from GCP Secret Manager."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.payload.data = b"secret-value"
            mock_client.access_secret_version.return_value = mock_response
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            result = client.get_secret("jwt-secret-key", environment="prod")

            assert result == "secret-value"
            mock_client.access_secret_version.assert_called_once()

    def test_get_secret_not_found(self):
        """Test secret retrieval when secret doesn't exist."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_client.access_secret_version.side_effect = gcp_exceptions.NotFound(
                "Secret not found"
            )
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            result = client.get_secret("nonexistent-secret", environment="prod")

            assert result is None

    def test_get_secret_fallback_to_env_var(self):
        """Test fallback to environment variable when GCP fails."""
        with (
            patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm,
            patch.dict(os.environ, {"SECRET_KEY": "env-secret-value"}),
        ):

            mock_client = Mock()
            mock_client.access_secret_version.side_effect = gcp_exceptions.NotFound(
                "Secret not found"
            )
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            result = client.get_secret(
                "jwt-secret-key", environment="prod", fallback_env_var="SECRET_KEY"
            )

            assert result == "env-secret-value"

    def test_get_secret_parse_json(self):
        """Test JSON parsing of secret values."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.payload.data = b'{"key": "value", "number": 42}'
            mock_client.access_secret_version.return_value = mock_response
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            result = client.get_secret(
                "json-secret", environment="prod", parse_json=True
            )

            assert result == {"key": "value", "number": 42}

    def test_create_secret_success(self):
        """Test successful secret creation."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.name = (
                "projects/test-project/secrets/prod-jwt-secret-key/versions/1"
            )
            mock_client.add_secret_version.return_value = mock_response
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            result = client.create_secret("jwt-secret-key", "new-secret-value", "prod")

            assert result is True
            mock_client.create_secret.assert_called_once()
            mock_client.add_secret_version.assert_called_once()

    def test_create_secret_already_exists(self):
        """Test secret creation when secret already exists."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_client.create_secret.side_effect = gcp_exceptions.AlreadyExists(
                "Secret exists"
            )
            mock_response = Mock()
            mock_response.name = (
                "projects/test-project/secrets/prod-jwt-secret-key/versions/1"
            )
            mock_client.add_secret_version.return_value = mock_response
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            result = client.create_secret("jwt-secret-key", "new-secret-value", "prod")

            assert result is True
            mock_client.add_secret_version.assert_called_once()

    def test_rotate_secret(self):
        """Test secret rotation."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.name = (
                "projects/test-project/secrets/prod-jwt-secret-key/versions/2"
            )
            mock_client.add_secret_version.return_value = mock_response
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            result = client.rotate_secret(
                "jwt-secret-key", "rotated-secret-value", "prod"
            )

            assert result is True
            mock_client.add_secret_version.assert_called_once()

    def test_list_secrets(self):
        """Test listing secrets for an environment."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_secret1 = Mock()
            mock_secret1.name = "projects/test-project/secrets/prod-jwt-secret-key"
            mock_secret2 = Mock()
            mock_secret2.name = "projects/test-project/secrets/prod-database-password"
            mock_secret3 = Mock()
            mock_secret3.name = "projects/test-project/secrets/dev-jwt-secret-key"

            mock_client.list_secrets.return_value = [
                mock_secret1,
                mock_secret2,
                mock_secret3,
            ]
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            secrets = client.list_secrets("prod")

            assert "jwt-secret-key" in secrets
            assert "database-password" in secrets
            assert "dev-jwt-secret-key" not in secrets

    def test_delete_secret(self):
        """Test secret deletion."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            result = client.delete_secret("jwt-secret-key", "prod")

            assert result is True
            mock_client.delete_secret.assert_called_once_with(
                request={"name": "projects/test-project/secrets/prod-jwt-secret-key"}
            )


@pytest.mark.unit
class TestGCPSecretManagerConvenienceFunctions:
    """Test the convenience functions for GCP Secret Manager."""

    def test_get_secret_client_singleton(self):
        """Test that get_secret_client returns a singleton instance."""
        # Reset the global singleton before testing
        import devcycle.core.secrets.gcp_secret_manager as gcp_module

        gcp_module._secret_client = None

        with patch(
            "devcycle.core.secrets.gcp_secret_manager.GCPSecretManagerClient"
        ) as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            client1 = get_secret_client()
            client2 = get_secret_client()

            assert client1 is client2
            mock_client_class.assert_called_once()

    def test_get_secret_convenience_function(self):
        """Test the get_secret convenience function."""
        with patch(
            "devcycle.core.secrets.gcp_secret_manager.get_secret_client"
        ) as mock_get_client:
            mock_client = Mock()
            mock_client.get_secret.return_value = "secret-value"
            mock_get_client.return_value = mock_client

            result = get_secret("jwt-secret-key", environment="prod")

            assert result == "secret-value"
            mock_client.get_secret.assert_called_once_with(
                "jwt-secret-key", "prod", None, False
            )

    def test_create_secret_convenience_function(self):
        """Test the create_secret convenience function."""
        with patch(
            "devcycle.core.secrets.gcp_secret_manager.get_secret_client"
        ) as mock_get_client:
            mock_client = Mock()
            mock_client.create_secret.return_value = True
            mock_get_client.return_value = mock_client

            result = create_secret("jwt-secret-key", "secret-value", "prod")

            assert result is True
            mock_client.create_secret.assert_called_once_with(
                "jwt-secret-key", "secret-value", "prod"
            )

    def test_rotate_secret_convenience_function(self):
        """Test the rotate_secret convenience function."""
        with patch(
            "devcycle.core.secrets.gcp_secret_manager.get_secret_client"
        ) as mock_get_client:
            mock_client = Mock()
            mock_client.rotate_secret.return_value = True
            mock_get_client.return_value = mock_client

            result = rotate_secret("jwt-secret-key", "new-secret-value", "prod")

            assert result is True
            mock_client.rotate_secret.assert_called_once_with(
                "jwt-secret-key", "new-secret-value", "prod"
            )


@pytest.mark.unit
class TestGCPSecretManagerErrorHandling:
    """Test error handling in GCP Secret Manager."""

    def test_gcp_client_initialization_error(self):
        """Test handling of GCP client initialization errors."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_sm.SecretManagerServiceClient.side_effect = Exception(
                "GCP initialization failed"
            )

            client = GCPSecretManagerClient(project_id="test-project")

            assert client.gcp_enabled is False
            assert client.client is None

    def test_secret_retrieval_error(self):
        """Test handling of secret retrieval errors."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_client.access_secret_version.side_effect = Exception("Network error")
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            result = client.get_secret("jwt-secret-key", environment="prod")

            assert result is None

    def test_secret_creation_error(self):
        """Test handling of secret creation errors."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_client.create_secret.side_effect = Exception("Creation failed")
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            result = client.create_secret("jwt-secret-key", "secret-value", "prod")

            assert result is False

    def test_invalid_json_parsing(self):
        """Test handling of invalid JSON in secret values."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.payload.data = b"invalid-json{"
            mock_client.access_secret_version.return_value = mock_response
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(project_id="test-project")
            result = client.get_secret(
                "json-secret", environment="prod", parse_json=True
            )

            # Should return the raw string when JSON parsing fails
            assert result == "invalid-json{"


@pytest.mark.unit
class TestGCPSecretManagerCaching:
    """Test caching behavior in GCP Secret Manager."""

    def test_cache_disabled(self):
        """Test behavior when caching is disabled."""
        with patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm:

            mock_client = Mock()
            mock_response = Mock()
            mock_response.payload.data = b"secret-value"
            mock_client.access_secret_version.return_value = mock_response
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            client = GCPSecretManagerClient(
                project_id="test-project", enable_caching=False
            )

            # First call
            result1 = client.get_secret("jwt-secret-key", environment="prod")
            # Second call
            result2 = client.get_secret("jwt-secret-key", environment="prod")

            assert result1 == "secret-value"
            assert result2 == "secret-value"
            # Should call GCP twice since caching is disabled
            assert mock_client.access_secret_version.call_count == 2
            # Cache should not be initialized
            assert client.cache is None

    def test_cache_clear_on_secret_update(self):
        """Test that cache is cleared when secret is updated."""
        with (
            patch("devcycle.core.secrets.gcp_secret_manager.secretmanager") as mock_sm,
            patch(
                "devcycle.core.secrets.gcp_secret_manager.get_cache"
            ) as mock_get_cache,
        ):

            mock_client = Mock()
            mock_response = Mock()
            mock_response.payload.data = b"secret-value"
            mock_response.name = (
                "projects/test-project/secrets/prod-jwt-secret-key/versions/1"
            )
            mock_client.access_secret_version.return_value = mock_response
            mock_client.add_secret_version.return_value = mock_response
            mock_sm.SecretManagerServiceClient.return_value = mock_client

            mock_cache = Mock()
            mock_cache.get.return_value = None  # Cache miss, should fetch from GCP
            mock_get_cache.return_value = mock_cache

            client = GCPSecretManagerClient(project_id="test-project")

            # Get secret (should be cached)
            result1 = client.get_secret("jwt-secret-key", environment="prod")
            assert result1 == "secret-value"

            # Update secret (should clear cache)
            client.create_secret("jwt-secret-key", "new-secret-value", "prod")

            # Verify cache was cleared
            mock_cache.delete.assert_called()

            # Get secret again (should fetch from GCP, not cache)
            result2 = client.get_secret("jwt-secret-key", environment="prod")
            assert result2 == "secret-value"

    def test_clear_all_caches(self):
        """Test clearing all cached secrets."""
        with patch(
            "devcycle.core.secrets.gcp_secret_manager.get_cache"
        ) as mock_get_cache:
            mock_cache = Mock()
            mock_cache.clear_pattern.return_value = 5
            mock_get_cache.return_value = mock_cache

            client = GCPSecretManagerClient(project_id="test-project")
            cleared_count = client.clear_all_caches()

            assert cleared_count == 5
            mock_cache.clear_pattern.assert_called_once_with("*")

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        with patch(
            "devcycle.core.secrets.gcp_secret_manager.get_cache"
        ) as mock_get_cache:
            mock_cache = Mock()
            mock_cache.get_stats.return_value = {
                "total_keys": 10,
                "redis_connected": True,
                "redis_version": "6.2.0",
                "used_memory": "1.2M",
                "connected_clients": 3,
            }
            mock_get_cache.return_value = mock_cache

            client = GCPSecretManagerClient(project_id="test-project")
            stats = client.get_cache_stats()

            assert stats["total_keys"] == 10
            assert stats["redis_connected"] is True
            assert stats["redis_version"] == "6.2.0"
            mock_cache.get_stats.assert_called_once()

    def test_get_cache_stats_disabled(self):
        """Test getting cache statistics when caching is disabled."""
        client = GCPSecretManagerClient(project_id="test-project", enable_caching=False)
        stats = client.get_cache_stats()

        assert stats["total_keys"] == 0
        assert stats["redis_connected"] is False
        assert stats["caching_enabled"] is False

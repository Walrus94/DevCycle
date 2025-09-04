"""
Integration tests for secret management functionality.

These tests verify the interaction between different components
of the secret management system with mocked external dependencies.
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from testcontainers.redis import RedisContainer

from devcycle.core.secrets.gcp_secret_manager import GCPSecretManagerClient
from devcycle.core.secrets.secret_config import (
    SecretAwareDatabaseConfig,
    SecretAwareHuggingFaceConfig,
    SecretAwareRedisConfig,
    SecretAwareSecurityConfig,
    get_production_secrets,
    validate_production_secrets,
)


@pytest.mark.integration
class TestSecretManagerIntegration:
    """Test integration between secret manager components."""

    @pytest.fixture(scope="class")
    def redis_container(self):
        """Start Redis container for integration tests."""
        with RedisContainer() as redis:
            # Wait for Redis to be ready
            redis.get_container_host_ip()
            yield redis

    @pytest.fixture(autouse=True)
    def clear_config_cache(self):
        """Clear the global config cache before each test."""
        from devcycle.core.config import set_config

        set_config(None)
        yield
        set_config(None)

    def test_secret_aware_configs_with_gcp_client(self, redis_container):
        """Test that secret-aware configs properly integrate with GCP client."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "testing",
                    "GOOGLE_CLOUD_PROJECT": "test-project",
                    "REDIS_HOST": redis_container.get_container_host_ip(),
                    "REDIS_PORT": str(redis_container.get_exposed_port(6379)),
                    "SECRET_KEY": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
                    "API_CORS_ORIGINS": '["https://example.com", "https://app.example.com"]',
                    "API_CORS_CREDENTIALS": "false",
                    "DB_PASSWORD": "test-db-password",  # Required for DevCycleConfig initialization
                },
            ),
            patch(
                "devcycle.core.secrets.gcp_secret_manager.secretmanager.SecretManagerServiceClient"
            ) as mock_gcp_client,
        ):
            # Mock GCP client with different secret values
            mock_gcp_client_instance = Mock()
            mock_response = Mock()

            # Configure the mock to return specific values for specific secret names
            def mock_access_secret_version(request):
                secret_name = request["name"]
                if "jwt-secret-key" in secret_name:
                    mock_response.payload.data.decode.return_value = "gcp-generated-secure-token-that-is-long-enough-for-validation-12345"
                elif "database-password" in secret_name:
                    mock_response.payload.data.decode.return_value = "gcp-db-password"
                elif "redis-password" in secret_name:
                    mock_response.payload.data.decode.return_value = (
                        "gcp-redis-password"
                    )
                elif "huggingface-token" in secret_name:
                    mock_response.payload.data.decode.return_value = "gcp-hf-token"
                else:
                    mock_response.payload.data.decode.return_value = (
                        "default-secret-value"
                    )
                return mock_response

            mock_gcp_client_instance.access_secret_version.side_effect = (
                mock_access_secret_version
            )
            mock_gcp_client.return_value = mock_gcp_client_instance

            # Create all secret-aware configs
            security_config = SecretAwareSecurityConfig()
            database_config = SecretAwareDatabaseConfig()
            redis_config = SecretAwareRedisConfig()
            huggingface_config = SecretAwareHuggingFaceConfig()

            # Debug: Check what the GCP client returned
            print(
                f"GCP client calls: {mock_gcp_client_instance.access_secret_version.call_count}"
            )
            print(f"Database config password: {database_config.password}")

            # Verify all configs got their secrets from GCP
            assert (
                security_config.secret_key
                == "gcp-generated-secure-token-that-is-long-enough-for-validation-12345"
            )
            assert database_config.password == "gcp-db-password"
            assert redis_config.password == "gcp-redis-password"
            assert huggingface_config.token == "gcp-hf-token"

            # Verify GCP client was called for each secret
            assert mock_gcp_client_instance.access_secret_version.call_count == 4

    def test_fallback_chain_integration(self, redis_container):
        """Test the complete fallback chain from GCP to environment variables."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "testing",
                    "SECRET_KEY": "env-generated-secure-token-that-is-long-enough-for-validation-12345",
                    "DB_PASSWORD": "env-db-password",
                    "REDIS_PASSWORD": "env-redis-password",
                    "HF_TOKEN": "env-hf-token",
                    "REDIS_HOST": redis_container.get_container_host_ip(),
                    "REDIS_PORT": str(redis_container.get_exposed_port(6379)),
                    "API_CORS_ORIGINS": '["https://example.com", "https://app.example.com"]',
                    "API_CORS_CREDENTIALS": "false",
                },
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):
            # Reload config to pick up new environment variables
            from devcycle.core.config import reload_config

            reload_config()

            # Mock GCP client to return None (simulating failure)
            mock_client = Mock()
            mock_client.get_secret.return_value = None
            mock_get_client.return_value = mock_client

            # Create all secret-aware configs
            security_config = SecretAwareSecurityConfig()
            database_config = SecretAwareDatabaseConfig()
            redis_config = SecretAwareRedisConfig()
            huggingface_config = SecretAwareHuggingFaceConfig()

            # Verify all configs fell back to environment variables
            assert (
                security_config.secret_key
                == "env-generated-secure-token-that-is-long-enough-for-validation-12345"
            )
            assert database_config.password == "env-db-password"
            assert redis_config.password == "env-redis-password"
            assert huggingface_config.token == "env-hf-token"

    def test_development_environment_integration(self, redis_container):
        """Test integration in development environment."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "development",
                "REDIS_HOST": redis_container.get_container_host_ip(),
                "REDIS_PORT": str(redis_container.get_exposed_port(6379)),
            },
        ):
            # Reload config to pick up new environment variables
            from devcycle.core.config import reload_config

            reload_config()
            # Create all secret-aware configs
            security_config = SecretAwareSecurityConfig()
            database_config = SecretAwareDatabaseConfig()
            redis_config = SecretAwareRedisConfig()
            huggingface_config = SecretAwareHuggingFaceConfig()

            # Verify development fallbacks
            assert len(security_config.secret_key) >= 32  # Generated secure secret
            assert database_config.password == "devcycle123"  # Default dev password
            assert redis_config.password is None  # No password in dev
            assert huggingface_config.token == ""  # Empty token in dev

    def test_caching_integration(self, redis_container):
        """Test that caching works correctly across multiple config instances."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "testing",
                    "GOOGLE_CLOUD_PROJECT": "test-project",
                    "REDIS_HOST": redis_container.get_container_host_ip(),
                    "REDIS_PORT": str(redis_container.get_exposed_port(6379)),
                    "SECRET_KEY": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
                    "DB_PASSWORD": "test-db-password",
                    "API_CORS_ORIGINS": '["https://example.com", "https://app.example.com"]',
                    "API_CORS_CREDENTIALS": "false",
                },
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
            patch("devcycle.core.cache.redis_cache.get_cache") as mock_get_cache,
        ):
            # Reload config to pick up new environment variables
            from devcycle.core.config import reload_config

            reload_config()

            # Mock the GCP Secret Manager client
            mock_gcp_client_instance = Mock()
            mock_response = Mock()
            mock_response.payload.data.decode.return_value = (
                "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
            )
            mock_gcp_client_instance.access_secret_version.return_value = mock_response
            mock_gcp_client_instance.get_secret.return_value = (
                "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
            )
            mock_get_client.return_value = mock_gcp_client_instance

            # Mock the Redis cache
            mock_cache_instance = Mock()
            mock_cache_instance.get.return_value = None  # Cache miss
            mock_cache_instance.set.return_value = True
            mock_get_cache.return_value = mock_cache_instance

            # Create multiple config instances
            config1 = SecretAwareSecurityConfig()
            config2 = SecretAwareSecurityConfig()

            # Both should get the same secret value
            assert (
                config1.secret_key
                == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
            )
            assert (
                config2.secret_key
                == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
            )

            # GCP client should be called for each config instance (caching doesn't work across separate instances)
            assert mock_gcp_client_instance.get_secret.call_count == 2

    def test_production_secrets_integration(self, redis_container):
        """Test the production secrets utility functions integration."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "testing",
                    "REDIS_HOST": redis_container.get_container_host_ip(),
                    "REDIS_PORT": str(redis_container.get_exposed_port(6379)),
                    "SECRET_KEY": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
                    "DB_PASSWORD": "test-db-password",
                    "API_CORS_ORIGINS": '["https://example.com", "https://app.example.com"]',
                    "API_CORS_CREDENTIALS": "false",
                },
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):
            # Reload config to pick up new environment variables
            from devcycle.core.config import reload_config

            reload_config()

            # Mock GCP client with specific secret values
            mock_client = Mock()
            mock_client.get_secret.side_effect = [
                "prod-jwt-secret",
                "prod-db-password",
                "prod-redis-password",
                "prod-hf-token",
                # Additional calls for validate_production_secrets
                "prod-jwt-secret",
                "prod-db-password",
            ]
            mock_get_client.return_value = mock_client

            # Test get_production_secrets
            secrets = get_production_secrets()
            expected_secrets = {
                "jwt-secret-key": "prod-jwt-secret",
                "database-password": "prod-db-password",
                "redis-password": "prod-redis-password",
                "huggingface-token": "prod-hf-token",
            }
            assert secrets == expected_secrets

            # Test validate_production_secrets
            result = validate_production_secrets()
            assert result is True

    def test_partial_secret_availability_integration(self, redis_container):
        """Test integration when only some secrets are available."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "testing",
                    "SECRET_KEY": "env-generated-secure-token-that-is-long-enough-for-validation-12345",
                    "DB_PASSWORD": "env-db-password",
                    "REDIS_HOST": redis_container.get_container_host_ip(),
                    "REDIS_PORT": str(redis_container.get_exposed_port(6379)),
                    "API_CORS_ORIGINS": '["https://example.com", "https://app.example.com"]',
                    "API_CORS_CREDENTIALS": "false",
                },
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):
            # Reload config to pick up new environment variables
            from devcycle.core.config import reload_config

            reload_config()

            # Mock GCP client to return None for all secrets
            mock_client = Mock()
            mock_client.get_secret.return_value = None
            mock_get_client.return_value = mock_client

            # Create configs - some should succeed, others should fail
            security_config = SecretAwareSecurityConfig()
            database_config = SecretAwareDatabaseConfig()

            # These should succeed with environment variable fallbacks
            assert (
                security_config.secret_key
                == "env-generated-secure-token-that-is-long-enough-for-validation-12345"
            )
            assert database_config.password == "env-db-password"

            # Redis and HuggingFace should use their development fallbacks
            redis_config = SecretAwareRedisConfig()
            huggingface_config = SecretAwareHuggingFaceConfig()

            assert redis_config.password is None
            assert huggingface_config.token == ""

    def test_environment_variable_priority_integration(self):
        """Test that environment variables take priority over GCP in non-production."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "staging",
                    "SECRET_KEY": "staging-generated-secure-token-that-is-long-enough-for-validation-12345",
                    "DB_PASSWORD": "staging-db-password",
                },
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):
            # Reload config to pick up new environment variables
            from devcycle.core.config import reload_config

            reload_config()

            # Mock GCP client (should not be called in staging)
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            # Create configs
            security_config = SecretAwareSecurityConfig()
            database_config = SecretAwareDatabaseConfig()

            # Should use environment variables directly
            assert (
                security_config.secret_key
                == "staging-generated-secure-token-that-is-long-enough-for-validation-12345"
            )
            assert database_config.password == "staging-db-password"

            # GCP client should not be called in staging
            mock_client.get_secret.assert_not_called()

    def test_error_handling_integration(self):
        """Test error handling across the secret management system."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "testing",
                    "GOOGLE_CLOUD_PROJECT": "test-project",
                    "SECRET_KEY": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
                    "DB_PASSWORD": "test-db-password",
                    "API_CORS_ORIGINS": '["https://example.com", "https://app.example.com"]',
                    "API_CORS_CREDENTIALS": "false",
                },
            ),
            patch(
                "devcycle.core.secrets.gcp_secret_manager.secretmanager.SecretManagerServiceClient"
            ) as mock_gcp_client,
        ):
            # Reload config to pick up new environment variables
            from devcycle.core.config import reload_config

            reload_config()

            # Mock GCP client to raise an exception
            mock_gcp_client_instance = Mock()
            mock_gcp_client_instance.access_secret_version.side_effect = Exception(
                "GCP connection failed"
            )
            mock_gcp_client.return_value = mock_gcp_client_instance

            # Create configs - should handle errors gracefully
            security_config = SecretAwareSecurityConfig()
            database_config = SecretAwareDatabaseConfig()

            # Should fall back to environment variables or development defaults
            # (depending on what's available)
            assert security_config.secret_key is not None
            assert database_config.password is not None

    def test_config_validation_integration(self, redis_container):
        """Test that configuration validation works across all secret-aware configs."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "testing",
                    "GOOGLE_CLOUD_PROJECT": "test-project",
                    "REDIS_HOST": redis_container.get_container_host_ip(),
                    "REDIS_PORT": str(redis_container.get_exposed_port(6379)),
                    "DB_PASSWORD": "test-db-password",
                    "API_CORS_ORIGINS": '["https://example.com", "https://app.example.com"]',
                    "API_CORS_CREDENTIALS": "false",
                },
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            # Mock GCP client with weak secrets
            mock_gcp_client_instance = Mock()
            call_count = 0

            def mock_get_secret(secret_id, environment=None, **kwargs):
                nonlocal call_count
                call_count += 1
                if secret_id == "jwt-secret-key":
                    return "weak-secret"  # Too short for security config
                elif secret_id == "database-password":
                    return "valid-db-password-12345"
                elif secret_id == "redis-password":
                    return "valid-redis-password-12345"
                elif secret_id == "huggingface-token":
                    return "valid-hf-token-12345"
                else:
                    return "default-secret-value"

            mock_gcp_client_instance.get_secret.side_effect = mock_get_secret
            mock_get_client.return_value = mock_gcp_client_instance

            # Security config should fail validation
            with pytest.raises(
                ValueError, match="Secret key must be at least 32 characters long"
            ):
                # Create SecretAwareSecurityConfig directly to test validation
                from devcycle.core.secrets.secret_config import (
                    SecretAwareSecurityConfig,
                )

                SecretAwareSecurityConfig()

            # Other configs should succeed
            database_config = SecretAwareDatabaseConfig()
            redis_config = SecretAwareRedisConfig()
            huggingface_config = SecretAwareHuggingFaceConfig()

            assert database_config.password == "valid-db-password-12345"
            assert redis_config.password == "valid-redis-password-12345"
            assert huggingface_config.token == "valid-hf-token-12345"

    def test_mixed_environment_integration(self):
        """Test integration with mixed environment configurations."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "testing",
                    "SECRET_KEY": "env-generated-secure-token-that-is-long-enough-for-validation-12345",
                    "DB_PASSWORD": "env-db-password",
                    "API_CORS_ORIGINS": '["https://example.com", "https://app.example.com"]',
                    "API_CORS_CREDENTIALS": "false",
                    # REDIS_PASSWORD and HF_TOKEN not set
                },
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):
            # Reload config to pick up new environment variables
            from devcycle.core.config import reload_config

            reload_config()

            # Mock GCP client to return None for all secrets
            mock_client = Mock()
            mock_client.get_secret.return_value = None
            mock_get_client.return_value = mock_client

            # Create all configs
            security_config = SecretAwareSecurityConfig()
            database_config = SecretAwareDatabaseConfig()
            redis_config = SecretAwareRedisConfig()
            huggingface_config = SecretAwareHuggingFaceConfig()

            # Verify mixed behavior
            assert (
                security_config.secret_key
                == "env-generated-secure-token-that-is-long-enough-for-validation-12345"
            )  # From env var
            assert database_config.password == "env-db-password"  # From env var
            assert redis_config.password is None  # Development fallback
            assert huggingface_config.token == ""  # Development fallback

    @pytest.mark.skip(
        reason="Secret rotation tests temporarily skipped - needs GCP mocking fixes"
    )
    def test_secret_rotation_integration(self, redis_container):
        """Test integration of secret rotation with configuration updates."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "testing",
                    "GOOGLE_CLOUD_PROJECT": "test-project",
                    "REDIS_HOST": redis_container.get_container_host_ip(),
                    "REDIS_PORT": str(redis_container.get_exposed_port(6379)),
                    "SECRET_KEY": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
                    "DB_PASSWORD": "test-db-password",
                    "API_CORS_ORIGINS": '["https://example.com", "https://app.example.com"]',
                    "API_CORS_CREDENTIALS": "false",
                },
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):
            # Mock GCP client
            mock_gcp_client_instance = Mock()

            # Configure the mock to return specific values for specific secret names
            def mock_get_secret(secret_id, environment=None, **kwargs):
                if secret_id == "jwt-secret-key":
                    return "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
                elif secret_id == "database-password":
                    return "valid-db-password-12345"
                elif secret_id == "redis-password":
                    return "valid-redis-password-12345"
                elif secret_id == "huggingface-token":
                    return "valid-hf-token-12345"
                else:
                    return "default-secret-value"

            mock_gcp_client_instance.get_secret.side_effect = mock_get_secret
            mock_get_client.return_value = mock_gcp_client_instance

            # Create initial config
            security_config = SecretAwareSecurityConfig()
            assert (
                security_config.secret_key
                == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
            )

            # Rotate the secret
            from devcycle.core.secrets.gcp_secret_manager import rotate_secret

            new_secret_value = (
                "x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4j3i2h1g0f9e8d7c6b5a4z3y2x1w0"
            )
            result = rotate_secret("jwt-secret-key", new_secret_value, "prod")
            assert result is True

            # Update the mock to return the new secret
            def mock_access_secret_version_updated(request):
                secret_name = request["name"]
                if "jwt-secret-key" in secret_name:
                    mock_response.payload.data.decode.return_value = new_secret_value
                elif "database-password" in secret_name:
                    mock_response.payload.data.decode.return_value = (
                        "valid-db-password-12345"
                    )
                elif "redis-password" in secret_name:
                    mock_response.payload.data.decode.return_value = (
                        "valid-redis-password-12345"
                    )
                elif "huggingface-token" in secret_name:
                    mock_response.payload.data.decode.return_value = (
                        "valid-hf-token-12345"
                    )
                else:
                    mock_response.payload.data.decode.return_value = (
                        "default-secret-value"
                    )
                return mock_response

            def mock_get_secret_updated(secret_id, environment=None, **kwargs):
                if secret_id == "jwt-secret-key":
                    return new_secret_value
                elif secret_id == "database-password":
                    return "valid-db-password-12345"
                elif secret_id == "redis-password":
                    return "valid-redis-password-12345"
                elif secret_id == "huggingface-token":
                    return "valid-hf-token-12345"
                else:
                    return "default-secret-value"

            mock_gcp_client_instance.access_secret_version.side_effect = (
                mock_access_secret_version_updated
            )
            mock_gcp_client_instance.get_secret.side_effect = mock_get_secret_updated

            # Clear the cache to force retrieval of the new secret
            from devcycle.core.secrets.gcp_secret_manager import get_secret_client

            secret_client = get_secret_client()
            if secret_client.cache:
                secret_client.cache.delete(
                    "devcycle:secrets:projects/test-project/secrets/prod-jwt-secret-key/versions/latest"
                )

            # Create new config instance (should get the rotated secret)
            new_security_config = SecretAwareSecurityConfig()
            assert new_security_config.secret_key == new_secret_value

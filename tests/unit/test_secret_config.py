"""
Unit tests for secret-aware configuration classes.

These tests focus on the configuration classes that integrate with GCP Secret Manager,
testing their behavior with mocked dependencies.
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from devcycle.core.secrets.secret_config import (
    SecretAwareDatabaseConfig,
    SecretAwareHuggingFaceConfig,
    SecretAwareRedisConfig,
    SecretAwareSecurityConfig,
    get_production_secrets,
    validate_production_secrets,
)


@pytest.mark.unit
class TestSecretAwareSecurityConfig:
    """Test the SecretAwareSecurityConfig class."""

    def test_get_secret_key_from_gcp_production(self):
        """Test secret key retrieval from GCP in production."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "testing"}),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.return_value = (
                "gcp-generated-secure-token-that-is-long-enough-for-validation-12345"
            )
            mock_get_client.return_value = mock_client

            config = SecretAwareSecurityConfig()

            assert (
                config.secret_key
                == "gcp-generated-secure-token-that-is-long-enough-for-validation-12345"
            )
            mock_client.get_secret.assert_called_once_with(
                "jwt-secret-key", environment="test"
            )

    def test_get_secret_key_fallback_to_env_var(self):
        """Test fallback to environment variable when GCP fails."""
        with (
            patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "testing",
                    "SECRET_KEY": "env-generated-secure-token-that-is-long-enough-for-validation-12345",
                },
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.return_value = None  # GCP fails
            mock_get_client.return_value = mock_client

            config = SecretAwareSecurityConfig()

            assert (
                config.secret_key
                == "env-generated-secure-token-that-is-long-enough-for-validation-12345"
            )

    def test_get_secret_key_development_fallback(self):
        """Test development fallback when no secrets are available."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "development"}),
            patch(
                "devcycle.core.secrets.secret_config.generate_secure_secret"
            ) as mock_generate,
        ):

            mock_generate.return_value = (
                "generated-secure-token-that-is-long-enough-for-validation-12345"
            )

            config = SecretAwareSecurityConfig()

            assert (
                config.secret_key
                == "generated-secure-token-that-is-long-enough-for-validation-12345"
            )

    def test_get_secret_key_production_error(self):
        """Test error when no secret is available in production."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "testing"}),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.return_value = None  # GCP fails
            mock_get_client.return_value = mock_client

            with pytest.raises(
                ValueError, match="SECRET_KEY must be set in production"
            ):
                SecretAwareSecurityConfig()

    def test_validate_secret_key_weak_patterns(self):
        """Test validation of weak secret key patterns."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # Test weak patterns
            weak_keys = [
                "dev-secret-key-change-in-production",
                "secret",
                "password",
                "123456",
                "admin",
                "test",
                "your-secret-key-here",
            ]

            for weak_key in weak_keys:
                with patch(
                    "devcycle.core.secrets.secret_config.SecretAwareSecurityConfig._get_secret_key",
                    return_value=weak_key,
                ):
                    with pytest.raises(
                        ValueError,
                        match="Secret key must be at least 32 characters long|Secret key contains weak patterns",
                    ):
                        SecretAwareSecurityConfig()

    def test_validate_secret_key_too_short(self):
        """Test validation of secret key length."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "development"}),
            patch(
                "devcycle.core.secrets.secret_config.SecretAwareSecurityConfig._get_secret_key",
                return_value="short",
            ),
        ):

            with pytest.raises(
                ValueError, match="Secret key must be at least 32 characters long"
            ):
                SecretAwareSecurityConfig()

    def test_validate_secret_key_production_defaults(self):
        """Test validation prevents production defaults in production."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "testing"}),
            patch(
                "devcycle.core.secrets.secret_config.SecretAwareSecurityConfig._get_secret_key",
                return_value="dev-secret-key-change-in-production",
            ),
        ):

            with pytest.raises(
                ValueError, match="Secret key contains weak patterns and is not secure"
            ):
                SecretAwareSecurityConfig()


@pytest.mark.unit
class TestSecretAwareDatabaseConfig:
    """Test the SecretAwareDatabaseConfig class."""

    def test_get_db_password_from_gcp_production(self):
        """Test database password retrieval from GCP in production."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "testing"}),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.return_value = "gcp-db-password"
            mock_get_client.return_value = mock_client

            config = SecretAwareDatabaseConfig()

            assert config.password == "gcp-db-password"
            mock_client.get_secret.assert_called_once_with(
                "database-password", environment="test"
            )

    def test_get_db_password_fallback_to_env_var(self):
        """Test fallback to environment variable when GCP fails."""
        with (
            patch.dict(
                os.environ, {"ENVIRONMENT": "testing", "DB_PASSWORD": "env-db-password"}
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.return_value = None  # GCP fails
            mock_get_client.return_value = mock_client

            config = SecretAwareDatabaseConfig()

            assert config.password == "env-db-password"

    def test_get_db_password_development_fallback(self):
        """Test development fallback for database password."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            config = SecretAwareDatabaseConfig()

            assert config.password == "devcycle123"

    def test_get_db_password_production_error(self):
        """Test error when no database password is available in production."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "testing"}),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.return_value = None  # GCP fails
            mock_get_client.return_value = mock_client

            with pytest.raises(
                ValueError, match="DB_PASSWORD must be set in production"
            ):
                SecretAwareDatabaseConfig()

    def test_database_url_generation(self):
        """Test database URL generation with password."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            config = SecretAwareDatabaseConfig(
                host="db.example.com", port=5432, username="testuser", database="testdb"
            )

            expected_url = (
                "postgresql://testuser:devcycle123@db.example.com:5432/testdb"
            )
            assert config.url == expected_url

    def test_database_url_generation_no_password(self):
        """Test database URL generation without password."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            config = SecretAwareDatabaseConfig(
                host="db.example.com", port=5432, username="testuser", database="testdb"
            )
            # Override password to empty
            config.password = ""

            expected_url = "postgresql://testuser@db.example.com:5432/testdb"
            assert config.url == expected_url

    def test_async_database_url_generation(self):
        """Test async database URL generation."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            config = SecretAwareDatabaseConfig(
                host="db.example.com", port=5432, username="testuser", database="testdb"
            )

            expected_url = (
                "postgresql+asyncpg://testuser:devcycle123@db.example.com:5432/testdb"
            )
            assert config.async_url == expected_url


@pytest.mark.unit
class TestSecretAwareRedisConfig:
    """Test the SecretAwareRedisConfig class."""

    def test_get_redis_password_from_gcp_production(self):
        """Test Redis password retrieval from GCP in production."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "testing"}),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.return_value = "gcp-redis-password"
            mock_get_client.return_value = mock_client

            config = SecretAwareRedisConfig()

            assert config.password == "gcp-redis-password"
            mock_client.get_secret.assert_called_once_with(
                "redis-password", environment="test"
            )

    def test_get_redis_password_fallback_to_env_var(self):
        """Test fallback to environment variable when GCP fails."""
        with (
            patch.dict(
                os.environ,
                {"ENVIRONMENT": "testing", "REDIS_PASSWORD": "env-redis-password"},
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.return_value = None  # GCP fails
            mock_get_client.return_value = mock_client

            config = SecretAwareRedisConfig()

            assert config.password == "env-redis-password"

    def test_get_redis_password_development_fallback(self):
        """Test development fallback for Redis password (no password)."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            config = SecretAwareRedisConfig()

            assert config.password is None


@pytest.mark.unit
class TestSecretAwareHuggingFaceConfig:
    """Test the SecretAwareHuggingFaceConfig class."""

    def test_get_hf_token_from_gcp_production(self):
        """Test HuggingFace token retrieval from GCP in production."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "testing"}),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.return_value = "gcp-hf-token"
            mock_get_client.return_value = mock_client

            config = SecretAwareHuggingFaceConfig()

            assert config.token == "gcp-hf-token"
            mock_client.get_secret.assert_called_once_with(
                "huggingface-token", environment="test"
            )

    def test_get_hf_token_fallback_to_env_var(self):
        """Test fallback to environment variable when GCP fails."""
        with (
            patch.dict(
                os.environ, {"ENVIRONMENT": "testing", "HF_TOKEN": "env-hf-token"}
            ),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.return_value = None  # GCP fails
            mock_get_client.return_value = mock_client

            config = SecretAwareHuggingFaceConfig()

            assert config.token == "env-hf-token"

    def test_get_hf_token_development_fallback(self):
        """Test development fallback for HuggingFace token (empty token)."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            config = SecretAwareHuggingFaceConfig()

            assert config.token == ""


@pytest.mark.unit
class TestProductionSecretsFunctions:
    """Test the production secrets utility functions."""

    def test_get_production_secrets(self):
        """Test getting all production secrets."""
        with patch(
            "devcycle.core.secrets.secret_config.get_secret_client"
        ) as mock_get_client:
            mock_client = Mock()
            mock_client.get_secret.side_effect = [
                "jwt-secret-value",
                "db-password-value",
                "redis-password-value",
                "hf-token-value",
            ]
            mock_get_client.return_value = mock_client

            secrets = get_production_secrets()

            expected_secrets = {
                "jwt-secret-key": "jwt-secret-value",
                "database-password": "db-password-value",
                "redis-password": "redis-password-value",
                "huggingface-token": "hf-token-value",
            }

            assert secrets == expected_secrets
            assert mock_client.get_secret.call_count == 4

    def test_get_production_secrets_partial(self):
        """Test getting production secrets when some are missing."""
        with patch(
            "devcycle.core.secrets.secret_config.get_secret_client"
        ) as mock_get_client:
            mock_client = Mock()
            mock_client.get_secret.side_effect = [
                "jwt-secret-value",
                None,  # database-password missing
                "redis-password-value",
                None,  # huggingface-token missing
            ]
            mock_get_client.return_value = mock_client

            secrets = get_production_secrets()

            expected_secrets = {
                "jwt-secret-key": "jwt-secret-value",
                "redis-password": "redis-password-value",
            }

            assert secrets == expected_secrets

    def test_validate_production_secrets_success(self):
        """Test successful validation of production secrets."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "testing"}),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.side_effect = [
                "jwt-secret-value",
                "db-password-value",
            ]
            mock_get_client.return_value = mock_client

            result = validate_production_secrets()

            assert result is True

    def test_validate_production_secrets_missing(self):
        """Test validation failure when production secrets are missing."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "production"}),
            patch(
                "devcycle.core.secrets.secret_config.get_secret_client"
            ) as mock_get_client,
        ):

            mock_client = Mock()
            mock_client.get_secret.side_effect = [
                "jwt-secret-value",
                None,  # database-password missing
            ]
            mock_get_client.return_value = mock_client

            result = validate_production_secrets()

            assert result is False

    def test_validate_production_secrets_non_production(self):
        """Test validation always succeeds in non-production environments."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            result = validate_production_secrets()

            assert result is True

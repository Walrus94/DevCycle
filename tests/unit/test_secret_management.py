"""
Test cases for secure secret management implementation (DOTM-471).
"""

import os
from unittest.mock import patch

import pytest

from devcycle.core.config.settings import SecurityConfig, generate_secure_secret


class TestSecretManagement:
    """Test secure secret management functionality."""

    def test_generate_secure_secret(self):
        """Test that secure secret generation works correctly."""
        secret = generate_secure_secret()

        # Should be a string
        assert isinstance(secret, str)

        # Should be at least 32 characters (base64 encoded 32 bytes = ~43 chars)
        assert len(secret) >= 32

        # Should be URL-safe base64
        assert all(c.isalnum() or c in "-_" for c in secret)

    def test_secret_key_validation_requires_value(self):
        """Test that secret key validation requires a value."""
        with pytest.raises(ValueError, match="Secret key is required"):
            SecurityConfig(secret_key="")

    def test_secret_key_validation_minimum_length(self):
        """Test that secret key validation enforces minimum length."""
        short_secret = "short"
        with pytest.raises(
            ValueError, match="Secret key must be at least 32 characters long"
        ):
            SecurityConfig(secret_key=short_secret)

    def test_secret_key_validation_weak_patterns(self):
        """Test that secret key validation rejects weak patterns."""
        weak_secrets = [
            "dev-secret-key-change-in-production",
            "my-secret-key-is-very-long-but-contains-secret",
            "password123456789012345678901234567890",
            "admin123456789012345678901234567890",
            "test123456789012345678901234567890",
        ]

        for weak_secret in weak_secrets:
            with pytest.raises(ValueError, match="Secret key contains weak patterns"):
                SecurityConfig(secret_key=weak_secret)

    def test_secret_key_validation_accepts_strong_secrets(self):
        """Test that secret key validation accepts strong secrets."""
        strong_secrets = [
            "22piwdzcXDSSYI0CIjyBerLC7wqO38QUHULJOGOIJD8",
            "YSsbOLE2Z3OayAYrwQ_dECxjyZ-MJBoqTGs-eiXEcAw",
            "DCLSgr17lUsF7Mc2llfrSsNmRs_duc1niwJyWk2jxzM",
            "a" * 32,  # Simple but long enough
        ]

        for strong_secret in strong_secrets:
            config = SecurityConfig(secret_key=strong_secret)
            assert config.secret_key == strong_secret

    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    def test_development_auto_generation(self):
        """Test that development environment auto-generates secure secrets."""
        config = SecurityConfig()

        # Should have a secret key
        assert config.secret_key is not None
        assert len(config.secret_key) >= 32

        # Should not contain weak patterns
        assert "dev-secret-key-change-in-production" not in config.secret_key
        assert "secret" not in config.secret_key.lower()

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_production_requires_explicit_secret(self):
        """Test that production environment requires explicit secret."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Input should be a valid string"):
            SecurityConfig()

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_production_rejects_old_default(self):
        """Test that production environment rejects the old hardcoded default."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Secret key contains weak patterns"):
            SecurityConfig(secret_key="dev-secret-key-change-in-production")

    @patch.dict(os.environ, {"ENVIRONMENT": "testing"})
    def test_testing_environment_behavior(self):
        """Test that testing environment requires explicit secret."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Input should be a valid string"):
            SecurityConfig()

    def test_secret_key_validation_case_insensitive(self):
        """Test that weak pattern detection is case insensitive."""
        weak_secrets = [
            "SECRET123456789012345678901234567890",
            "Password123456789012345678901234567890",
            "ADMIN123456789012345678901234567890",
        ]

        for weak_secret in weak_secrets:
            with pytest.raises(ValueError, match="Secret key contains weak patterns"):
                SecurityConfig(secret_key=weak_secret)

    def test_secret_key_validation_edge_cases(self):
        """Test edge cases for secret key validation."""
        # Exactly 32 characters should pass
        exactly_32 = "a" * 32
        config = SecurityConfig(secret_key=exactly_32)
        assert config.secret_key == exactly_32

        # 31 characters should fail
        too_short = "a" * 31
        with pytest.raises(
            ValueError, match="Secret key must be at least 32 characters long"
        ):
            SecurityConfig(secret_key=too_short)

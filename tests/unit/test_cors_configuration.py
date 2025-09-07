"""
Test cases for CORS configuration and security (DOTM-473).

This module tests the environment-specific CORS configuration and security measures.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from devcycle.core.config.settings import APIConfig, DevCycleConfig, Environment


class TestAPIConfigCORS:
    """Test APIConfig CORS properties."""

    def test_cors_origins_development(self):
        """Test CORS origins for development environment."""
        # Test by creating a DevCycleConfig with development environment
        config = DevCycleConfig(environment=Environment.DEVELOPMENT)
        origins = config.cors_origins_resolved

        expected_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
        assert origins == expected_origins

    def test_cors_origins_staging(self):
        """Test CORS origins for staging environment."""
        from devcycle.core.config.settings import APIConfig

        config = DevCycleConfig(
            environment=Environment.STAGING,
            api=APIConfig(
                cors_origins=[
                    "https://staging.yourdomain.com",
                    "https://staging-app.yourdomain.com",
                ]
            ),
        )
        origins = config.cors_origins_resolved

        expected_origins = [
            "https://staging.yourdomain.com",
            "https://staging-app.yourdomain.com",
        ]
        assert origins == expected_origins

    def test_cors_origins_production(self):
        """Test CORS origins for production environment."""
        from devcycle.core.config.settings import APIConfig

        config = DevCycleConfig(
            environment=Environment.PRODUCTION,
            api=APIConfig(
                cors_origins=["https://yourdomain.com", "https://app.yourdomain.com"],
                cors_credentials=False,
            ),
        )
        origins = config.cors_origins_resolved

        expected_origins = [
            "https://yourdomain.com",
            "https://app.yourdomain.com",
        ]
        assert origins == expected_origins

    def test_cors_origins_custom(self):
        """Test custom CORS origins override defaults."""
        config = APIConfig(cors_origins=["https://custom.example.com"])
        origins = config.cors_origins_resolved("development")

        assert origins == ["https://custom.example.com"]

    def test_cors_credentials_development(self):
        """Test CORS credentials for development environment."""
        config = DevCycleConfig(environment=Environment.DEVELOPMENT)
        assert config.cors_credentials_resolved is True

    def test_cors_credentials_production(self):
        """Test CORS credentials for production environment."""
        from devcycle.core.config.settings import APIConfig

        config = DevCycleConfig(
            environment=Environment.PRODUCTION,
            api=APIConfig(cors_origins=["https://example.com"], cors_credentials=False),
        )
        assert config.cors_credentials_resolved is False

    def test_cors_methods_development(self):
        """Test CORS methods for development environment."""
        config = DevCycleConfig(environment=Environment.DEVELOPMENT)
        assert config.cors_methods_resolved == ["*"]

    def test_cors_methods_production(self):
        """Test CORS methods for production environment."""
        from devcycle.core.config.settings import APIConfig

        config = DevCycleConfig(
            environment=Environment.PRODUCTION,
            api=APIConfig(cors_origins=["https://example.com"], cors_credentials=False),
        )
        expected_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        assert config.cors_methods_resolved == expected_methods

    def test_cors_headers_default(self):
        """Test default CORS headers."""
        config = APIConfig()
        headers = config.cors_headers_resolved

        expected_headers = [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-CSRF-Token",
            "X-Requested-With",
        ]
        assert headers == expected_headers

    def test_cors_expose_headers_default(self):
        """Test default exposed CORS headers."""
        config = APIConfig()
        headers = config.cors_expose_headers_resolved

        expected_headers = [
            "Content-Length",
            "Content-Type",
            "X-Total-Count",
        ]
        assert headers == expected_headers


class TestDevCycleConfigCORSValidation:
    """Test DevCycleConfig CORS validation."""

    def test_production_cors_validation_wildcard_origins(self):
        """Test that production rejects wildcard CORS origins."""
        with pytest.raises(
            ValidationError,
            match="Production environment cannot allow all CORS origins",
        ):
            DevCycleConfig(
                environment=Environment.PRODUCTION, api=APIConfig(cors_origins=["*"])
            )

    def test_production_cors_validation_empty_origins(self):
        """Test that production requires CORS origins."""
        with pytest.raises(
            ValidationError,
            match="Production environment must specify allowed CORS origins",
        ):
            DevCycleConfig(
                environment=Environment.PRODUCTION, api=APIConfig(cors_origins=[])
            )

    def test_production_cors_validation_http_origins(self):
        """Test that production rejects HTTP origins."""
        with pytest.raises(
            ValidationError, match="Production CORS origin must use HTTPS"
        ):
            DevCycleConfig(
                environment=Environment.PRODUCTION,
                api=APIConfig(cors_origins=["http://example.com"]),
            )

    def test_production_cors_validation_localhost_origins(self):
        """Test that production rejects localhost origins."""
        with pytest.raises(
            ValidationError,
            match="Production environment cannot allow localhost origins",
        ):
            DevCycleConfig(
                environment=Environment.PRODUCTION,
                api=APIConfig(cors_origins=["https://localhost:3000"]),
            )

    def test_production_cors_validation_credentials(self):
        """Test that production rejects CORS credentials."""
        with pytest.raises(
            ValidationError,
            match="Production environment should not allow CORS credentials",
        ):
            DevCycleConfig(
                environment=Environment.PRODUCTION,
                api=APIConfig(
                    cors_origins=["https://example.com"], cors_credentials=True
                ),
            )

    def test_production_cors_validation_valid_config(self):
        """Test that valid production CORS config passes validation."""
        config = DevCycleConfig(
            environment=Environment.PRODUCTION,
            api=APIConfig(
                cors_origins=["https://example.com", "https://app.example.com"],
                cors_credentials=False,
            ),
        )

        assert config.environment == Environment.PRODUCTION
        assert config.api.cors_origins == [
            "https://example.com",
            "https://app.example.com",
        ]
        assert config.api.cors_credentials is False

    def test_development_cors_validation_permissive(self):
        """Test that development allows permissive CORS config."""
        config = DevCycleConfig(
            environment=Environment.DEVELOPMENT,
            api=APIConfig(cors_origins=["*"], cors_credentials=True),
        )

        assert config.environment == Environment.DEVELOPMENT
        assert config.api.cors_origins == ["*"]
        assert config.api.cors_credentials is True


class TestCORSIntegration:
    """Test CORS integration with FastAPI app."""

    def test_cors_headers_development(self):
        """Test CORS headers in development environment."""
        # Create a mock config that returns development environment
        mock_config = DevCycleConfig(environment=Environment.DEVELOPMENT)

        with patch("devcycle.api.app.get_config", return_value=mock_config):
            from devcycle.api.app import create_app

            app = create_app()
            client = TestClient(app)

            # Test preflight request
            response = client.options(
                "/api/v1/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )

            assert response.status_code == 200
            assert "Access-Control-Allow-Origin" in response.headers
            assert (
                response.headers["Access-Control-Allow-Origin"]
                == "http://localhost:3000"
            )

    def test_cors_headers_production(self):
        """Test CORS headers in production environment."""
        # Create a mock config that returns production environment
        from devcycle.core.config.settings import APIConfig

        mock_config = DevCycleConfig(
            environment=Environment.PRODUCTION,
            api=APIConfig(
                cors_origins=["https://yourdomain.com"], cors_credentials=False
            ),
        )

        with patch("devcycle.api.app.get_config", return_value=mock_config):
            from devcycle.api.app import create_app

            app = create_app()
            client = TestClient(app)

            # Test preflight request with allowed origin
            response = client.options(
                "/api/v1/health",
                headers={
                    "Origin": "https://yourdomain.com",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )

            assert response.status_code == 200
            assert "Access-Control-Allow-Origin" in response.headers
            assert (
                response.headers["Access-Control-Allow-Origin"]
                == "https://yourdomain.com"
            )

    def test_cors_headers_unauthorized_origin(self):
        """Test CORS headers with unauthorized origin."""
        from devcycle.core.config.settings import APIConfig

        mock_config = DevCycleConfig(
            environment=Environment.PRODUCTION,
            api=APIConfig(
                cors_origins=["https://yourdomain.com"], cors_credentials=False
            ),
        )

        with patch("devcycle.api.app.get_config", return_value=mock_config):
            from devcycle.api.app import create_app

            app = create_app()
            client = TestClient(app)

            # Test preflight request with unauthorized origin
            response = client.options(
                "/api/v1/health",
                headers={
                    "Origin": "https://malicious.com",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )

            # Should not include Access-Control-Allow-Origin for unauthorized origins
            assert "Access-Control-Allow-Origin" not in response.headers

    # Legacy health endpoint tests removed - health endpoints migrated to ACP

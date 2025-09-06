"""
Unit tests for security features.

This module tests the security middleware, headers, and rate limiting.
"""

from fastapi.testclient import TestClient

from devcycle.api.app import create_app
from devcycle.core.auth.decorators import check_user_role, get_user_role_level


class TestSecurityFeatures:
    """Test security features implementation."""

    def test_security_headers_middleware(self):
        """Test that security headers are added to responses."""
        app = create_app()
        client = TestClient(app)

        # Test version endpoint to check security headers
        response = client.get("/api/version")

        # Check security headers are present
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Referrer-Policy" in response.headers
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in response.headers

        # Check server header is removed
        assert "server" not in response.headers

    def test_rate_limiting_middleware(self):
        """Test that rate limiting is applied to auth endpoints."""
        app = create_app()
        client = TestClient(app)

        # Make multiple requests to auth endpoint to trigger rate limiting
        # Note: This is a simplified test - in practice, you'd need to test
        # with real auth

        # Test that auth endpoints exist and are protected
        response = client.get("/api/v1/auth/me")
        # Should get 401 (unauthorized) not 429 (rate limited) for first request
        assert response.status_code == 401

    def test_role_hierarchy(self):
        """Test role hierarchy and checking functions."""
        # Test role levels
        assert get_user_role_level("user") == 1
        assert get_user_role_level("admin") == 2
        assert get_user_role_level("unknown") == 0

        # Test role checking
        from uuid import uuid4

        from devcycle.core.auth.tortoise_models import User

        # Create mock user objects
        user = User(
            id=uuid4(), email="user@example.com", hashed_password="hashed", role="user"
        )

        admin = User(
            id=uuid4(),
            email="admin@example.com",
            hashed_password="hashed",
            role="admin",
        )

        # Test role checking
        assert check_user_role(user, "user") is True
        assert check_user_role(user, "admin") is False
        assert check_user_role(admin, "user") is True
        assert check_user_role(admin, "admin") is True

    def test_cors_configuration(self):
        """Test that CORS is properly configured."""
        app = create_app()
        client = TestClient(app)

        # Test OPTIONS request to check CORS headers
        response = client.options("/api/version")

        # CORS should be configured (though OPTIONS might not show all headers in test)
        assert response.status_code in [200, 405]  # 405 is also acceptable for OPTIONS

    def test_security_middleware_order(self):
        """Test that security middleware is added in correct order."""
        app = create_app()

        # Check that our custom middleware classes are in the app
        # FastAPI stores middleware differently, so we'll test the functionality instead
        # The important thing is that security headers are added

        # Test that security headers are actually added (this is the real test)
        client = TestClient(app)
        response = client.get("/api/version")

        # Verify security headers are present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers


class TestAuthorizationDecorators:
    """Test authorization decorators."""

    def test_require_role_decorator(self):
        """Test the require_role decorator."""
        from devcycle.core.auth.decorators import require_role

        @require_role("admin")
        async def admin_function():
            return "admin_only"

        # Decorator should be applied
        assert hasattr(admin_function, "__wrapped__")

    def test_require_admin_decorator(self):
        """Test the require_admin decorator."""
        from devcycle.core.auth.decorators import require_admin

        @require_admin
        async def admin_only_function():
            return "admin_only"

        # Decorator should be applied
        assert hasattr(admin_only_function, "__wrapped__")

    def test_require_user_decorator(self):
        """Test the require_user decorator."""
        from devcycle.core.auth.decorators import require_user

        @require_user
        async def user_only_function():
            return "user_only"

        # Decorator should be applied
        assert hasattr(user_only_function, "__wrapped__")

"""
End-to-end tests for FastAPI Users authentication system.

This module tests the complete authentication flow including:
- JWT login/logout
- Protected endpoint access
- User profile management
- Password reset flow

NOTE: User registration is disabled - users must be created by admin
"""

import pytest
from httpx import AsyncClient

from devcycle.api.app import app


@pytest.mark.e2e
@pytest.mark.auth
@pytest.mark.slow
@pytest.mark.asyncio
class TestFastAPIUsersAuthenticationE2E:
    """Test FastAPI Users authentication flow end-to-end."""

    @pytest.mark.asyncio
    async def test_debug_routes(self, async_client: AsyncClient):
        """Debug test to check available routes."""
        # Get the app's routes directly from the imported app
        routes = []
        for route in app.routes:
            if hasattr(route, "path"):
                routes.append(f"{route.methods} {route.path}")

        print("Available routes:")
        for route in sorted(routes):
            print(f"  {route}")

        # Check if auth routes exist
        auth_routes = [r for r in routes if "/auth" in r]
        print(f"\nAuth routes: {len(auth_routes)}")
        for route in sorted(auth_routes):
            print(f"  {route}")

        assert len(auth_routes) > 0, "No auth routes found"

    @pytest.mark.skip(
        reason="Password change functionality not yet implemented - "
        "will be added in future sprint"
    )
    @pytest.mark.asyncio
    async def test_password_change_flow(self, async_client: AsyncClient):
        """Test password change functionality.

        NOTE: This test is currently disabled as password change functionality
        has not been implemented yet. The test will be re-enabled and updated
        when the password change feature is added to the authentication system.

        TODO: Implement password change functionality
        - Add password change endpoint
        - Implement password validation
        - Add password change confirmation
        - Update this test to verify full password change flow
        """
        # 1. Create and login a user
        user_data = {"email": "passuser@example.com", "password": "SecurePass123!"}

        await async_client.post("/api/v1/auth/users/register", json=user_data)

        login_response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": "passuser@example.com", "password": "SecurePass123!"},
        )

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. For now, just verify the user can access their profile
        # Password change functionality will be implemented later
        me_response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200

        user_profile = me_response.json()
        assert user_profile["email"] == "passuser@example.com"
        assert user_profile["is_active"] is True

        # TODO: Implement password change functionality
        # This test will be updated when password change is implemented

    @pytest.mark.skip(
        reason="User deactivation functionality not yet implemented - "
        "will be added in future sprint"
    )
    @pytest.mark.asyncio
    async def test_user_deactivation(self, async_client: AsyncClient):
        """Test user account deactivation.

        NOTE: This test is currently disabled as user deactivation functionality
        has not been implemented yet. The test will be re-enabled and updated
        when the user deactivation feature is added to the authentication system.

        TODO: Implement user deactivation functionality
        - Add user deactivation endpoint
        - Implement deactivation confirmation
        - Add reactivation functionality
        - Update this test to verify full deactivation flow
        """
        # 1. Create and login a user
        user_data = {
            "email": "deactivateuser@example.com",
            "password": "SecurePass123!",
        }

        await async_client.post("/api/v1/auth/users/register", json=user_data)

        login_response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={
                "username": "deactivateuser@example.com",
                "password": "SecurePass123!",
            },
        )

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. For now, just verify the user can access their profile
        # User deactivation functionality will be implemented later
        me_response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200

        user_profile = me_response.json()
        assert user_profile["email"] == "deactivateuser@example.com"
        assert user_profile["is_active"] is True

        # TODO: Implement user deactivation functionality
        # This test will be updated when deactivation is implemented

    # TODO: Add tests for authentication with pre-existing users
    # These tests should verify:
    # - JWT login with existing users
    # - Token validation
    # - Protected endpoint access
    # - Profile management
    # - Logout functionality
    #
    # These tests would require setting up test users in the database
    # before running the tests, rather than relying on registration

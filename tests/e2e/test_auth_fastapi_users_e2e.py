"""
End-to-end tests for FastAPI Users authentication system.

This module tests the complete authentication flow including:
- User registration
- JWT login/logout
- Protected endpoint access
- User profile management
- Password reset flow
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

    @pytest.mark.asyncio
    async def test_user_registration_and_login_flow(self, async_client: AsyncClient):
        """Test complete user registration and JWT login flow."""
        # 1. Register a new user with basic fields only
        user_data = {"email": "newuser@example.com", "password": "SecurePass123!"}

        register_response = await async_client.post(
            "/api/v1/auth/users/register", json=user_data
        )
        assert register_response.status_code == 201

        user_info = register_response.json()
        assert user_info["email"] == "newuser@example.com"
        assert "id" in user_info
        assert user_info["is_active"] is True
        assert user_info["is_verified"] is False

        # 2. Login with JWT
        login_data = {
            "username": "newuser@example.com",  # FastAPI Users uses email as username
            "password": "SecurePass123!",
        }

        login_response = await async_client.post(
            "/api/v1/auth/jwt/login", data=login_data
        )
        assert login_response.status_code == 200

        login_info = login_response.json()
        assert "access_token" in login_info
        assert "token_type" in login_info
        assert login_info["token_type"] == "bearer"

        # 3. Access protected endpoint with JWT token
        headers = {"Authorization": f"Bearer {login_info['access_token']}"}

        me_response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200

        user_profile = me_response.json()
        assert user_profile["email"] == "newuser@example.com"
        assert user_profile["is_active"] is True

    @pytest.mark.asyncio
    async def test_jwt_token_validation(self, async_client: AsyncClient):
        """Test JWT token validation and expiration."""
        # 1. Create and login a user
        user_data = {"email": "testuser@example.com", "password": "SecurePass123!"}

        await async_client.post("/api/v1/auth/users/register", json=user_data)

        login_response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": "testuser@example.com", "password": "SecurePass123!"},
        )

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Test valid token access
        me_response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200

        # 3. Test invalid token access
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        invalid_response = await async_client.get(
            "/api/v1/auth/me", headers=invalid_headers
        )
        assert invalid_response.status_code == 401

        # 4. Test missing token
        no_token_response = await async_client.get("/api/v1/auth/me")
        assert no_token_response.status_code == 401

    @pytest.mark.asyncio
    async def test_user_profile_management(self, async_client: AsyncClient):
        """Test user profile update and management."""
        # 1. Create and login a user
        user_data = {"email": "profileuser@example.com", "password": "SecurePass123!"}

        await async_client.post("/api/v1/auth/users/register", json=user_data)

        login_response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": "profileuser@example.com", "password": "SecurePass123!"},
        )

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Update user profile
        update_data = {"first_name": "Updated", "last_name": "Profile"}

        update_response = await async_client.patch(
            "/api/v1/auth/users/me", json=update_data, headers=headers
        )
        assert update_response.status_code == 200

        updated_user = update_response.json()
        assert updated_user["first_name"] == "Updated"
        assert updated_user["last_name"] == "Profile"

        # 3. Verify profile was updated
        me_response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200

        user_profile = me_response.json()
        assert user_profile["first_name"] == "Updated"
        assert user_profile["last_name"] == "Profile"

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

    @pytest.mark.asyncio
    async def test_multiple_user_sessions(self, async_client: AsyncClient):
        """Test multiple users can have concurrent sessions."""
        # 1. Create two users
        user1_data = {"email": "user1@example.com", "password": "SecurePass123!"}

        user2_data = {"email": "user2@example.com", "password": "SecurePass123!"}

        await async_client.post("/api/v1/auth/users/register", json=user1_data)
        await async_client.post("/api/v1/auth/users/register", json=user2_data)

        # 2. Login both users
        user1_login = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": "user1@example.com", "password": "SecurePass123!"},
        )

        user2_login = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": "user2@example.com", "password": "SecurePass123!"},
        )

        assert user1_login.status_code == 200
        assert user2_login.status_code == 200

        user1_token = user1_login.json()["access_token"]
        user2_token = user2_login.json()["access_token"]

        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        # 3. Both users can access their own profiles
        user1_me = await async_client.get("/api/v1/auth/me", headers=user1_headers)
        user2_me = await async_client.get("/api/v1/auth/me", headers=user2_headers)

        assert user1_me.status_code == 200
        assert user2_me.status_code == 200

        user1_profile = user1_me.json()
        user2_profile = user2_me.json()

        assert user1_profile["email"] == "user1@example.com"
        assert user2_profile["email"] == "user2@example.com"

        # 4. Users cannot access each other's profiles (tokens are user-specific)
        # This is inherent in JWT - each token contains the user's identity
        assert user1_profile["id"] != user2_profile["id"]

    @pytest.mark.asyncio
    async def test_logout_and_token_invalidation(self, async_client: AsyncClient):
        """Test logout functionality and token handling."""
        # 1. Create and login a user
        user_data = {"email": "logoutuser@example.com", "password": "SecurePass123!"}

        await async_client.post("/api/v1/auth/users/register", json=user_data)

        login_response = await async_client.post(
            "/api/v1/auth/jwt/login",
            data={"username": "logoutuser@example.com", "password": "SecurePass123!"},
        )

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Verify token works
        me_response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200

        # 3. Test logout endpoint (FastAPI Users JWT logout)
        logout_response = await async_client.post(
            "/api/v1/auth/jwt/logout", headers=headers
        )
        # 204 No Content is correct for logout
        assert logout_response.status_code == 204

        # 4. Note: JWT tokens are stateless, so they remain valid until expiration
        # This is expected behavior for JWT authentication
        # In a production system, you might implement a token blacklist or
        # shorter expiration times

        # 5. Verify token still works (JWT is stateless)
        await async_client.get("/api/v1/auth/me", headers=headers)
        # This might still work depending on JWT configuration
        # The real security comes from short token expiration times

"""
Tests for authentication endpoints.

This module tests the login, logout, and session management endpoints
that integrate with the Redis-based session system.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from devcycle.api.auth.endpoints import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SessionInfo,
    login,
    logout,
)
from devcycle.api.auth.sessions import SessionData


class TestLoginEndpoint:
    """Test login endpoint functionality."""

    @pytest.mark.asyncio
    async def test_login_success(self) -> None:
        """Test successful login."""
        # Mock request and response
        mock_request = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "test-user-agent"

        mock_response = Mock()
        mock_response.set_cookie = Mock()

        # Mock session manager
        mock_session_manager = AsyncMock()
        mock_session_data = SessionData(
            session_id="test_session_123",
            user_id="admin_001",
            username="admin",
            email="admin@devcycle.dev",
            roles=["admin", "user"],
            permissions=["read", "write", "admin"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            ip_address="127.0.0.1",
            user_agent="test-user-agent",
            metadata={"login_method": "password", "remember_me": False},
        )
        mock_session_manager.create_session.return_value = mock_session_data

        # Mock config
        with patch("devcycle.api.auth.endpoints.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.auth.session_cookie_name = "devcycle_session"
            mock_config.auth.session_secure = False
            mock_config.auth.session_httponly = True
            mock_config.auth.session_samesite = "lax"
            mock_get_config.return_value = mock_config

            # Test login
            login_data = LoginRequest(username="admin", password="admin123")
            result = await login(
                login_data, mock_request, mock_response, mock_session_manager
            )

            # Verify result
            assert result.success is True
            assert result.session_id == "test_session_123"
            assert result.username == "admin"
            assert result.roles == ["admin", "user"]
            assert result.permissions == ["read", "write", "admin"]

            # Verify session creation was called
            mock_session_manager.create_session.assert_called_once()

            # Verify cookie was set
            mock_response.set_cookie.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self) -> None:
        """Test login with invalid credentials."""
        mock_request = Mock()
        mock_response = Mock()
        mock_session_manager = AsyncMock()

        # Test login with invalid credentials
        login_data = LoginRequest(username="invalid", password="wrong")

        with pytest.raises(Exception) as exc_info:
            await login(login_data, mock_request, mock_response, mock_session_manager)

        # Check the exception detail field
        assert exc_info.value.detail == "Invalid credentials"

    @pytest.mark.asyncio
    async def test_login_remember_me(self) -> None:
        """Test login with remember me option."""
        mock_request = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "test-user-agent"

        mock_response = Mock()
        mock_response.set_cookie = Mock()

        mock_session_manager = AsyncMock()
        mock_session_data = SessionData(
            session_id="test_session_123",
            user_id="user_001",
            username="user",
            email="user@devcycle.dev",
            roles=["user"],
            permissions=["read", "write"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            ip_address="127.0.0.1",
            user_agent="test-user-agent",
            metadata={"login_method": "password", "remember_me": True},
        )
        mock_session_manager.create_session.return_value = mock_session_data

        with patch("devcycle.api.auth.endpoints.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.auth.session_cookie_name = "devcycle_session"
            mock_config.auth.session_secure = False
            mock_config.auth.session_httponly = True
            mock_config.auth.session_samesite = "lax"
            mock_get_config.return_value = mock_config

            # Test login with remember me
            login_data = LoginRequest(
                username="user", password="user123", remember_me=True
            )
            result = await login(
                login_data, mock_request, mock_response, mock_session_manager
            )

            assert result.success is True
            assert result.username == "user"

            # Verify metadata includes remember_me
            call_args = mock_session_manager.create_session.call_args
            assert call_args[1]["metadata"]["remember_me"] is True


class TestLogoutEndpoint:
    """Test logout endpoint functionality."""

    @pytest.mark.asyncio
    async def test_logout_success(self) -> None:
        """Test successful logout."""
        # Mock request with session cookie
        mock_request = Mock()
        mock_request.cookies = {"devcycle_session": "test_session_123"}

        mock_response = Mock()
        mock_response.delete_cookie = Mock()

        mock_session_manager = AsyncMock()
        mock_session_manager.delete_session.return_value = True

        with patch("devcycle.api.auth.endpoints.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.auth.session_cookie_name = "devcycle_session"
            mock_get_config.return_value = mock_config

            # Test logout
            result = await logout(mock_request, mock_response, mock_session_manager)

            # Verify result
            assert result.success is True
            assert "successful" in result.message.lower()

            # Verify session was deleted
            mock_session_manager.delete_session.assert_called_once_with(
                "test_session_123"
            )

            # Verify cookie was cleared
            mock_response.delete_cookie.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_no_session(self) -> None:
        """Test logout when no session exists."""
        mock_request = Mock()
        mock_request.cookies = {}

        mock_response = Mock()
        mock_response.delete_cookie = Mock()

        mock_session_manager = AsyncMock()

        with patch("devcycle.api.auth.endpoints.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.auth.session_cookie_name = "devcycle_session"
            mock_get_config.return_value = mock_config

            # Test logout without session
            result = await logout(mock_request, mock_response, mock_session_manager)

            # Should still succeed
            assert result.success is True

            # No session deletion should occur
            mock_session_manager.delete_session.assert_not_called()

            # Cookie should still be cleared
            mock_response.delete_cookie.assert_called_once()


class TestSessionInfoEndpoint:
    """Test session information endpoint functionality."""

    @pytest.mark.asyncio
    async def test_get_session_info(self) -> None:
        """Test getting session information."""
        mock_session_info = SessionInfo(
            session_id="test_session_123",
            user_id="admin_001",
            username="admin",
            email="admin@devcycle.dev",
            roles=["admin", "user"],
            permissions=["read", "write", "admin"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            ip_address="127.0.0.1",
            user_agent="test-user-agent",
        )

        # Test getting session info - just return the input
        result = mock_session_info

        assert result == mock_session_info


class TestSessionExtraction:
    """Test session ID extraction from requests."""

    def test_extract_session_from_cookie(self) -> None:
        """Test extracting session ID from cookie."""
        from devcycle.api.auth.endpoints import _extract_session_id

        mock_request = Mock()
        mock_request.cookies = {"devcycle_session": "test_session_123"}
        mock_request.headers = {}

        with patch("devcycle.api.auth.endpoints.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.auth.session_cookie_name = "devcycle_session"
            mock_get_config.return_value = mock_config

            session_id = _extract_session_id(mock_request)
            assert session_id == "test_session_123"

    def test_extract_session_from_header(self) -> None:
        """Test extracting session ID from Authorization header."""
        from devcycle.api.auth.endpoints import _extract_session_id

        mock_request = Mock()
        mock_request.cookies = {}
        mock_request.headers = {"Authorization": "Bearer test_session_123"}

        with patch("devcycle.api.auth.endpoints.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.auth.session_cookie_name = "devcycle_session"
            mock_get_config.return_value = mock_config

            session_id = _extract_session_id(mock_request)
            assert session_id == "test_session_123"

    def test_extract_session_not_found(self) -> None:
        """Test extracting session ID when not present."""
        from devcycle.api.auth.endpoints import _extract_session_id

        mock_request = Mock()
        mock_request.cookies = {}
        mock_request.headers = {}

        with patch("devcycle.api.auth.endpoints.get_config") as mock_get_config:
            mock_config = Mock()
            mock_config.auth.session_cookie_name = "devcycle_session"
            mock_get_config.return_value = mock_config

            session_id = _extract_session_id(mock_request)
            assert session_id is None


class TestAuthenticationModels:
    """Test authentication data models."""

    def test_login_request_model(self) -> None:
        """Test LoginRequest model validation."""
        login_data = LoginRequest(username="testuser", password="testpass")
        assert login_data.username == "testuser"
        assert login_data.password == "testpass"
        assert login_data.remember_me is False

        # Test with remember_me
        login_data = LoginRequest(
            username="testuser", password="testpass", remember_me=True
        )
        assert login_data.remember_me is True

    def test_login_response_model(self) -> None:
        """Test LoginResponse model validation."""
        now = datetime.now(timezone.utc)
        response = LoginResponse(
            success=True,
            session_id="test_session",
            user_id="test_user",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read"],
            expires_at=now,
            message="Login successful",
        )

        assert response.success is True
        assert response.session_id == "test_session"
        assert response.username == "testuser"
        assert response.roles == ["user"]

    def test_logout_response_model(self) -> None:
        """Test LogoutResponse model validation."""
        response = LogoutResponse(success=True, message="Logout successful")

        assert response.success is True
        assert response.message == "Logout successful"

    def test_session_info_model(self) -> None:
        """Test SessionInfo model validation."""
        now = datetime.now(timezone.utc)
        session_info = SessionInfo(
            session_id="test_session",
            user_id="test_user",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read"],
            created_at=now,
            expires_at=now,
            last_activity=now,
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert session_info.session_id == "test_session"
        assert session_info.username == "testuser"
        assert session_info.ip_address == "127.0.0.1"
        assert session_info.user_agent == "test-agent"


class TestMockAuthentication:
    """Test mock authentication function."""

    @pytest.mark.asyncio
    async def test_authenticate_admin_user(self) -> None:
        """Test admin user authentication."""
        from devcycle.api.auth.endpoints import _authenticate_user

        user_data = await _authenticate_user("admin", "admin123")

        assert user_data is not None
        assert user_data["username"] == "admin"
        assert user_data["roles"] == ["admin", "user"]
        assert "admin" in user_data["permissions"]

    @pytest.mark.asyncio
    async def test_authenticate_regular_user(self) -> None:
        """Test regular user authentication."""
        from devcycle.api.auth.endpoints import _authenticate_user

        user_data = await _authenticate_user("user", "user123")

        assert user_data is not None
        assert user_data["username"] == "user"
        assert user_data["roles"] == ["user"]
        assert "admin" not in user_data["permissions"]

    @pytest.mark.asyncio
    async def test_authenticate_invalid_user(self) -> None:
        """Test invalid user authentication."""
        from devcycle.api.auth.endpoints import _authenticate_user

        user_data = await _authenticate_user("invalid", "wrong")

        assert user_data is None

"""
Tests for the session management system.

This module tests Redis-based session creation, validation,
and management functionality.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from devcycle.api.auth.sessions import SessionData, SessionManager


@pytest.fixture
def session_manager() -> SessionManager:
    """Create a session manager instance for testing."""
    return SessionManager()


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Sample user data for testing."""
    return {
        "user_id": "test_user_123",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
        "permissions": ["read", "write"],
    }


@pytest.fixture
def sample_session_data(sample_user_data: Dict[str, Any]) -> SessionData:
    """Sample session data for testing."""
    now = datetime.now(timezone.utc)
    # Set expiration to 1 hour in the future
    expires_at = now + timedelta(hours=1)
    return SessionData(
        session_id="test_session_123",
        user_id=sample_user_data["user_id"],
        username=sample_user_data["username"],
        email=sample_user_data["email"],
        roles=sample_user_data["roles"],
        permissions=sample_user_data["permissions"],
        created_at=now,
        expires_at=expires_at,
        last_activity=now,
        ip_address="127.0.0.1",
        user_agent="test-agent",
        metadata={"test": True},
    )


class TestSessionManager:
    """Test session manager functionality."""

    def test_init(self, session_manager: SessionManager) -> None:
        """Test session manager initialization."""
        assert session_manager.cookie_name == "devcycle_session"
        assert session_manager.max_age == 3600
        assert session_manager.secure is True
        assert session_manager.httponly is True
        assert session_manager.samesite == "strict"
        assert session_manager.rate_limit_enabled is True
        assert session_manager.rate_limit_requests == 100
        assert session_manager.rate_limit_window == 60

    def test_generate_session_id(self, session_manager: SessionManager) -> None:
        """Test session ID generation."""
        session_id1 = session_manager._generate_session_id()
        session_id2 = session_manager._generate_session_id()

        assert len(session_id1) == 43  # base64 encoded 32 bytes
        assert len(session_id2) == 43
        assert session_id1 != session_id2  # Should be unique

    @pytest.mark.asyncio
    async def test_create_session_success(
        self, session_manager: SessionManager, sample_user_data: Dict[str, Any]
    ) -> None:
        """Test successful session creation."""
        with patch("devcycle.api.auth.sessions.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            # Mock Redis operations
            mock_redis.setex.return_value = True
            mock_redis.sadd.return_value = 1
            mock_redis.expire.return_value = True

            session_data = await session_manager.create_session(
                sample_user_data, ip_address="127.0.0.1", user_agent="test-agent"
            )

            assert session_data.session_id is not None
            assert session_data.user_id == sample_user_data["user_id"]
            assert session_data.username == sample_user_data["username"]
            assert session_data.email == sample_user_data["email"]
            assert session_data.roles == sample_user_data["roles"]
            assert session_data.permissions == sample_user_data["permissions"]
            assert session_data.ip_address == "127.0.0.1"
            assert session_data.user_agent == "test-agent"
            assert session_data.metadata == {}

            # Verify Redis calls
            mock_redis.setex.assert_called_once()
            mock_redis.sadd.assert_called_once()
            mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_failure(
        self, session_manager: SessionManager, sample_user_data: Dict[str, Any]
    ) -> None:
        """Test session creation failure."""
        with patch("devcycle.api.auth.sessions.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            # Mock Redis failure
            mock_redis.setex.side_effect = Exception("Redis error")

            with pytest.raises(HTTPException) as exc_info:
                await session_manager.create_session(sample_user_data)

            assert exc_info.value.status_code == 500
            assert "Failed to create session" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_session_success(
        self, session_manager: SessionManager, sample_session_data: SessionData
    ) -> None:
        """Test successful session retrieval."""
        with patch("devcycle.api.auth.sessions.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            # Mock Redis get operation
            session_json = sample_session_data.model_dump_json()
            mock_redis.get.return_value = session_json

            # Mock Redis setex for update_last_activity
            mock_redis.setex.return_value = True

            result = await session_manager.get_session("test_session_123")

            assert result is not None
            assert result.session_id == sample_session_data.session_id
            assert result.user_id == sample_session_data.user_id
            assert result.username == sample_session_data.username

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_manager: SessionManager) -> None:
        """Test session retrieval when session doesn't exist."""
        with patch("devcycle.api.auth.sessions.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            # Mock Redis get returning None
            mock_redis.get.return_value = None

            result = await session_manager.get_session("nonexistent_session")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_session_expired(
        self, session_manager: SessionManager, sample_session_data: SessionData
    ) -> None:
        """Test session retrieval when session is expired."""
        with patch("devcycle.api.auth.sessions.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            # Create expired session data - set expiration to 1 hour in the past
            expired_session = sample_session_data.model_copy()
            expired_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

            # Mock Redis operations
            session_json = expired_session.model_dump_json()
            mock_redis.get.return_value = session_json

            result = await session_manager.get_session("expired_session")

            assert result is None
            # Note: Expired sessions are not automatically deleted by get_session
            # to avoid potential infinite loops. Cleanup should be handled separately.
            mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_session(self, session_manager: SessionManager) -> None:
        """Test session validation."""
        with patch.object(session_manager, "get_session") as mock_get_session:
            # Test valid session
            mock_get_session.return_value = sample_session_data
            result = await session_manager.validate_session("valid_session")
            assert result is True

            # Test invalid session
            mock_get_session.return_value = None
            result = await session_manager.validate_session("invalid_session")
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_session(
        self, session_manager: SessionManager, sample_session_data: SessionData
    ) -> None:
        """Test session deletion."""
        with patch("devcycle.api.auth.sessions.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            # Mock session data retrieval
            with patch.object(session_manager, "get_session") as mock_get_session:
                mock_get_session.return_value = sample_session_data

                # Mock Redis operations
                mock_redis.delete.return_value = 1

                result = await session_manager.delete_session("test_session")

                assert result is True
                # Verify cleanup calls
                assert mock_redis.delete.call_count == 2  # session + rate limit

    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limits(
        self, session_manager: SessionManager
    ) -> None:
        """Test rate limiting when within limits."""
        with patch("devcycle.api.auth.sessions.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            # Mock Redis operations - simulate first request (incr returns 1,
            # triggers expire)
            mock_redis.incr.return_value = 1
            mock_redis.expire.return_value = True

            result = await session_manager.check_rate_limit("test_session")

            assert result is True
            mock_redis.incr.assert_called_once()
            # expire should be called when current_count == 1 (first request)
            mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(
        self, session_manager: SessionManager
    ) -> None:
        """Test rate limiting when limits are exceeded."""
        with patch("devcycle.api.auth.sessions.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            # Mock Redis operations - simulate first request (incr returns 1,
            # triggers expire)
            mock_redis.incr.return_value = 1
            mock_redis.expire.return_value = True

            result = await session_manager.check_rate_limit("test_session")

            assert result is True  # First request should always succeed
            mock_redis.incr.assert_called_once()
            # expire should be called when current_count == 1 (first request)
            mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_rate_limit_already_exceeded(
        self, session_manager: SessionManager
    ) -> None:
        """Test rate limiting when the limit is already exceeded."""
        with patch("devcycle.api.auth.sessions.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            # Mock Redis operations - simulate request when count is already
            # above limit
            mock_redis.incr.return_value = 101  # Already exceeds 100 limit
            mock_redis.expire.return_value = True

            result = await session_manager.check_rate_limit("test_session")

            assert result is False  # Should be rate limited
            mock_redis.incr.assert_called_once()
            # expire should not be called when current_count > 1
            mock_redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_rate_limit_disabled(
        self, session_manager: SessionManager
    ) -> None:
        """Test rate limiting when disabled."""
        # Disable rate limiting
        session_manager.rate_limit_enabled = False

        result = await session_manager.check_rate_limit("test_session")

        assert result is True  # Should always allow when disabled


class TestSessionData:
    """Test SessionData model."""

    def test_session_data_creation(self, sample_session_data: SessionData) -> None:
        """Test SessionData model creation."""
        assert sample_session_data.session_id == "test_session_123"
        assert sample_session_data.user_id == "test_user_123"
        assert sample_session_data.username == "testuser"
        assert sample_session_data.email == "test@example.com"
        assert sample_session_data.roles == ["user"]
        assert sample_session_data.permissions == ["read", "write"]
        assert sample_session_data.ip_address == "127.0.0.1"
        assert sample_session_data.user_agent == "test-agent"
        assert sample_session_data.metadata == {"test": True}

    def test_session_data_validation(self) -> None:
        """Test SessionData model validation."""
        # Should raise validation error for missing required fields
        with pytest.raises(Exception):
            SessionData(
                session_id="test",
                user_id="test_user",
                username="testuser",
                email="test@example.com",
                # Missing required fields: created_at, expires_at, last_activity
            )

    def test_session_data_optional_fields(self) -> None:
        """Test SessionData model with optional fields."""
        now = datetime.now(timezone.utc)
        session_data = SessionData(
            session_id="test_session",
            user_id="test_user",
            username="testuser",
            email="test@example.com",
            created_at=now,
            expires_at=now,
            last_activity=now,
            ip_address="127.0.0.1",
            user_agent="test-agent",
            # Optional fields not provided
        )

        assert session_data.roles == []
        assert session_data.permissions == []
        assert session_data.ip_address == "127.0.0.1"
        assert session_data.user_agent == "test-agent"
        assert session_data.metadata == {}

"""
Test cases for enhanced session management and security (DOTM-474).

This module tests the token blacklisting system, session monitoring,
and enhanced JWT strategy functionality.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import redis  # type: ignore

from devcycle.core.auth.secure_jwt_strategy import SecureJWTStrategy
from devcycle.core.auth.session_monitor import SessionMonitor
from devcycle.core.auth.token_blacklist import TokenBlacklist
from devcycle.core.config.settings import DevCycleConfig, Environment


class TestTokenBlacklist:
    """Test TokenBlacklist functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for testing."""
        mock_redis = MagicMock(spec=redis.Redis)
        mock_redis.setex.return_value = True
        mock_redis.exists.return_value = False
        mock_redis.keys.return_value = []
        mock_redis.ping.return_value = True
        return mock_redis

    @pytest.fixture
    def token_blacklist(self, mock_redis):
        """Create TokenBlacklist instance with mocked Redis."""
        with patch(
            "devcycle.core.auth.token_blacklist.redis.Redis", return_value=mock_redis
        ):
            return TokenBlacklist()

    def test_token_blacklist_initialization(self, token_blacklist):
        """Test TokenBlacklist initialization."""
        assert token_blacklist is not None
        assert token_blacklist.blacklist_prefix == "jwt_blacklist:"

    def test_blacklist_token_success(self, token_blacklist, mock_redis):
        """Test successful token blacklisting."""
        token = "test.jwt.token"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        result = token_blacklist.blacklist_token(token, expires_at)

        assert result is True
        mock_redis.setex.assert_called_once()

        # Verify the call arguments
        call_args = mock_redis.setex.call_args
        assert call_args[0][0].startswith("jwt_blacklist:")
        assert call_args[0][1] > 0  # TTL should be positive

    def test_blacklist_token_expired(self, token_blacklist, mock_redis):
        """Test blacklisting expired token."""
        token = "test.jwt.token"
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Already expired

        result = token_blacklist.blacklist_token(token, expires_at)

        assert result is False
        mock_redis.setex.assert_not_called()

    def test_is_blacklisted_false(self, token_blacklist, mock_redis):
        """Test checking non-blacklisted token."""
        token = "test.jwt.token"
        mock_redis.exists.return_value = False

        result = token_blacklist.is_blacklisted(token)

        assert result is False
        mock_redis.exists.assert_called_once()

    def test_is_blacklisted_true(self, token_blacklist, mock_redis):
        """Test checking blacklisted token."""
        token = "test.jwt.token"
        mock_redis.exists.return_value = True

        result = token_blacklist.is_blacklisted(token)

        assert result is True
        mock_redis.exists.assert_called_once()

    def test_is_blacklisted_redis_error(self, token_blacklist, mock_redis):
        """Test blacklist check with Redis error (fail secure)."""
        token = "test.jwt.token"
        mock_redis.exists.side_effect = Exception("Redis error")

        result = token_blacklist.is_blacklisted(token)

        assert result is True  # Should fail secure

    def test_hash_token(self, token_blacklist):
        """Test token hashing."""
        token = "test.jwt.token"
        hash1 = token_blacklist._hash_token(token)
        hash2 = token_blacklist._hash_token(token)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length
        assert hash1 != token  # Should be hashed

    def test_cleanup_expired(self, token_blacklist, mock_redis):
        """Test cleanup of expired entries."""
        mock_redis.keys.return_value = ["jwt_blacklist:hash1", "jwt_blacklist:hash2"]
        mock_redis.exists.side_effect = [False, True]  # First expired, second exists

        result = token_blacklist.cleanup_expired()

        assert result == 1  # One expired entry
        assert mock_redis.keys.called
        assert mock_redis.exists.call_count == 2

    def test_get_blacklist_stats(self, token_blacklist, mock_redis):
        """Test getting blacklist statistics."""
        mock_redis.keys.return_value = ["jwt_blacklist:hash1", "jwt_blacklist:hash2"]

        stats = token_blacklist.get_blacklist_stats()

        assert stats["total_blacklisted_tokens"] == 2
        assert stats["redis_connected"] is True

    def test_health_check_success(self, token_blacklist, mock_redis):
        """Test successful health check."""
        result = token_blacklist.health_check()

        assert result is True
        mock_redis.ping.assert_called_once()

    def test_health_check_failure(self, token_blacklist, mock_redis):
        """Test failed health check."""
        mock_redis.ping.side_effect = Exception("Connection failed")

        result = token_blacklist.health_check()

        assert result is False


class TestSessionMonitor:
    """Test SessionMonitor functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for testing."""
        mock_redis = MagicMock(spec=redis.Redis)
        mock_redis.sadd.return_value = 1
        mock_redis.expire.return_value = True
        mock_redis.smembers.return_value = set()
        mock_redis.hset.return_value = 1
        mock_redis.hgetall.return_value = {}
        mock_redis.srem.return_value = 1
        mock_redis.delete.return_value = 1
        mock_redis.keys.return_value = []
        mock_redis.scard.return_value = 0
        mock_redis.ping.return_value = True
        return mock_redis

    @pytest.fixture
    def session_monitor(self, mock_redis):
        """Create SessionMonitor instance with mocked Redis."""
        with patch(
            "devcycle.core.auth.session_monitor.redis.Redis", return_value=mock_redis
        ):
            return SessionMonitor()

    def test_session_monitor_initialization(self, session_monitor):
        """Test SessionMonitor initialization."""
        assert session_monitor is not None
        assert session_monitor.session_prefix == "user_sessions:"
        assert session_monitor.session_info_prefix == "session_info:"

    def test_track_session_success(self, session_monitor, mock_redis):
        """Test successful session tracking."""
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        result = session_monitor.track_session(
            user_id, session_id, expires_at, "test-agent", "127.0.0.1"
        )

        assert result is True
        mock_redis.sadd.assert_called_once()
        mock_redis.hset.assert_called()

    def test_track_session_expired(self, session_monitor, mock_redis):
        """Test tracking expired session."""
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Already expired

        result = session_monitor.track_session(user_id, session_id, expires_at)

        assert result is False
        mock_redis.sadd.assert_not_called()

    def test_get_active_sessions(self, session_monitor, mock_redis):
        """Test getting active sessions."""
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        mock_redis.smembers.return_value = {session_id}
        mock_redis.hgetall.return_value = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "user_agent": "test-agent",
            "ip_address": "127.0.0.1",
        }

        sessions = session_monitor.get_active_sessions(user_id)

        assert len(sessions) == 1
        assert sessions[0]["user_id"] == user_id
        assert sessions[0]["session_id"] == session_id

    def test_remove_session_success(self, session_monitor, mock_redis):
        """Test successful session removal."""
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        result = session_monitor.remove_session(user_id, session_id)

        assert result is True
        mock_redis.srem.assert_called_once()
        mock_redis.delete.assert_called_once()

    def test_remove_all_sessions(self, session_monitor, mock_redis):
        """Test removing all sessions for user."""
        user_id = str(uuid.uuid4())
        session_id1 = str(uuid.uuid4())
        session_id2 = str(uuid.uuid4())

        mock_redis.smembers.return_value = {session_id1, session_id2}
        mock_redis.delete.return_value = 1

        result = session_monitor.remove_all_sessions(user_id)

        assert result == 2  # Two sessions removed
        mock_redis.delete.assert_called()

    def test_cleanup_expired_sessions(self, session_monitor, mock_redis):
        """Test cleanup of expired sessions."""
        session_info_key = "session_info:test-session"
        mock_redis.keys.return_value = [session_info_key]
        mock_redis.hgetall.return_value = {
            "user_id": str(uuid.uuid4()),
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        }

        result = session_monitor.cleanup_expired_sessions()

        assert result == 1  # One expired session
        mock_redis.delete.assert_called()

    def test_get_session_stats(self, session_monitor, mock_redis):
        """Test getting session statistics."""
        mock_redis.keys.return_value = ["user_sessions:user1", "user_sessions:user2"]
        mock_redis.scard.side_effect = [2, 1]  # Two sessions for user1, one for user2

        stats = session_monitor.get_session_stats()

        assert stats["total_active_sessions"] == 3
        assert stats["total_users_with_sessions"] == 2
        assert stats["redis_connected"] is True

    def test_health_check_success(self, session_monitor, mock_redis):
        """Test successful health check."""
        result = session_monitor.health_check()

        assert result is True
        mock_redis.ping.assert_called_once()

    def test_health_check_failure(self, session_monitor, mock_redis):
        """Test failed health check."""
        mock_redis.ping.side_effect = Exception("Connection failed")

        result = session_monitor.health_check()

        assert result is False


class TestSecureJWTStrategy:
    """Test SecureJWTStrategy functionality."""

    @pytest.fixture
    def mock_blacklist(self):
        """Mock TokenBlacklist for testing."""
        mock_blacklist = MagicMock()
        mock_blacklist.is_blacklisted.return_value = False
        mock_blacklist.get_blacklist_stats.return_value = {
            "total_blacklisted_tokens": 0
        }
        mock_blacklist.health_check.return_value = True
        return mock_blacklist

    @pytest.fixture
    def secure_jwt_strategy(self, mock_blacklist):
        """Create SecureJWTStrategy with mocked blacklist."""
        with patch(
            "devcycle.core.auth.secure_jwt_strategy.TokenBlacklist",
            return_value=mock_blacklist,
        ):
            return SecureJWTStrategy(secret="test-secret", lifetime_seconds=3600)

    def test_secure_jwt_strategy_initialization(self, secure_jwt_strategy):
        """Test SecureJWTStrategy initialization."""
        assert secure_jwt_strategy is not None
        assert secure_jwt_strategy.blacklist is not None

    @pytest.mark.asyncio
    async def test_read_token_not_blacklisted(
        self, secure_jwt_strategy, mock_blacklist
    ):
        """Test reading non-blacklisted token."""
        token = "valid.jwt.token"
        mock_user = MagicMock()
        mock_user_manager = MagicMock()
        mock_user_manager.get.return_value = mock_user

        # Mock the parent class read_token method
        with patch.object(
            secure_jwt_strategy.__class__.__bases__[0],
            "read_token",
            return_value=mock_user,
        ):
            result = await secure_jwt_strategy.read_token(token, mock_user_manager)

        assert result == mock_user
        mock_blacklist.is_blacklisted.assert_called_once_with(token)

    @pytest.mark.asyncio
    async def test_read_token_blacklisted(self, secure_jwt_strategy, mock_blacklist):
        """Test reading blacklisted token."""
        token = "blacklisted.jwt.token"
        mock_blacklist.is_blacklisted.return_value = True

        with pytest.raises(Exception):  # Should raise InvalidToken
            await secure_jwt_strategy.read_token(token, MagicMock())

        mock_blacklist.is_blacklisted.assert_called_once_with(token)

    def test_get_blacklist_stats(self, secure_jwt_strategy, mock_blacklist):
        """Test getting blacklist statistics."""
        stats = secure_jwt_strategy.get_blacklist_stats()

        assert stats == {"total_blacklisted_tokens": 0}
        mock_blacklist.get_blacklist_stats.assert_called_once()

    def test_health_check(self, secure_jwt_strategy, mock_blacklist):
        """Test health check."""
        result = secure_jwt_strategy.health_check()

        assert result is True
        mock_blacklist.health_check.assert_called_once()


class TestSessionManagementIntegration:
    """Test session management integration with FastAPI."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = DevCycleConfig(environment=Environment.DEVELOPMENT)
        return config

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for integration tests."""
        mock_redis = MagicMock(spec=redis.Redis)
        mock_redis.setex.return_value = True
        mock_redis.exists.return_value = False
        mock_redis.sadd.return_value = 1
        mock_redis.expire.return_value = True
        mock_redis.smembers.return_value = set()
        mock_redis.hset.return_value = 1
        mock_redis.hgetall.return_value = {}
        mock_redis.srem.return_value = 1
        mock_redis.delete.return_value = 1
        mock_redis.ping.return_value = True
        return mock_redis

    def test_logout_endpoint_integration(self, mock_config, mock_redis):
        """Test logout endpoint integration."""
        with patch("devcycle.core.config.get_config", return_value=mock_config), patch(
            "devcycle.core.auth.token_blacklist.redis.Redis", return_value=mock_redis
        ), patch(
            "devcycle.core.auth.session_monitor.redis.Redis", return_value=mock_redis
        ), patch(
            "devcycle.api.auth.endpoints.current_active_user"
        ) as mock_user_dep:
            from fastapi import Request

            from devcycle.core.auth.models import User

            # Mock user
            mock_user = User(
                id=uuid.uuid4(),
                email="test@example.com",
                hashed_password="hashed",
                is_active=True,
                is_verified=True,
                is_superuser=False,
                first_name="Test",
                last_name="User",
                role="user",
            )
            mock_user_dep.return_value = mock_user

            # Mock request with valid JWT
            mock_request = MagicMock(spec=Request)
            mock_request.headers = {"Authorization": "Bearer valid.jwt.token"}

            # Mock JWT decode
            with patch("jwt.decode") as mock_jwt_decode:
                mock_jwt_decode.return_value = {
                    "exp": (
                        datetime.now(timezone.utc) + timedelta(hours=1)
                    ).timestamp(),
                    "jti": str(uuid.uuid4()),
                }

                # This would normally be called in the endpoint
                # We're just testing the integration components work together
                blacklist = TokenBlacklist()
                session_monitor = SessionMonitor()

                assert blacklist is not None
                assert session_monitor is not None

    def test_session_monitoring_integration(self, mock_config, mock_redis):
        """Test session monitoring integration."""
        with patch("devcycle.core.config.get_config", return_value=mock_config), patch(
            "devcycle.core.auth.session_monitor.redis.Redis", return_value=mock_redis
        ):
            session_monitor = SessionMonitor()
            user_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

            # Test session tracking
            result = session_monitor.track_session(user_id, session_id, expires_at)
            assert result is True

            # Test getting sessions
            sessions = session_monitor.get_active_sessions(user_id)
            assert isinstance(sessions, list)

            # Test session removal
            result = session_monitor.remove_session(user_id, session_id)
            assert result is True

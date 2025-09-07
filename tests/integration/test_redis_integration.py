"""
Integration tests for Redis functionality.

This module tests Redis integration with real Redis instances using testcontainers,
covering caching, session monitoring, and token blacklisting functionality.
"""

import time
from uuid import uuid4

import pytest
import redis  # type: ignore[import-untyped]
from testcontainers.redis import RedisContainer

from devcycle.core.auth.session_monitor import SessionMonitor
from devcycle.core.auth.token_blacklist import TokenBlacklist
from devcycle.core.cache.redis_cache import RedisCache


@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests for Redis functionality."""

    @pytest.fixture(scope="class")
    def redis_container(self):
        """Start Redis container for integration tests."""
        with RedisContainer("redis:7-alpine") as redis_container:
            yield redis_container

    @pytest.fixture
    def redis_client(self, redis_container):
        """Create Redis client connected to test container."""
        return redis.Redis(
            host=redis_container.get_container_host_ip(),
            port=redis_container.get_exposed_port(6379),
            decode_responses=True,
            db=0,
        )

    @pytest.fixture
    def redis_cache(self, redis_client):
        """Create RedisCache instance with test Redis client."""
        with pytest.MonkeyPatch().context() as m:
            # Mock the Redis client creation to use our test client
            m.setattr(
                "devcycle.core.cache.redis_cache.redis.Redis",
                lambda **kwargs: redis_client,
            )
            return RedisCache("test:cache:")

    @pytest.fixture
    def session_monitor(self, redis_client):
        """Create SessionMonitor instance with test Redis client."""
        with pytest.MonkeyPatch().context() as m:
            # Mock the Redis client creation to use our test client
            m.setattr(
                "devcycle.core.auth.session_monitor.redis.Redis",
                lambda **kwargs: redis_client,
            )
            return SessionMonitor()

    @pytest.fixture
    def token_blacklist(self, redis_client):
        """Create TokenBlacklist instance with test Redis client."""
        with pytest.MonkeyPatch().context() as m:
            # Mock the Redis client creation to use our test client
            m.setattr(
                "devcycle.core.auth.token_blacklist.redis.Redis",
                lambda **kwargs: redis_client,
            )
            return TokenBlacklist()

    def test_redis_connection(self, redis_client):
        """Test basic Redis connection."""
        # Test ping
        assert redis_client.ping() is True

        # Test basic operations
        redis_client.set("test_key", "test_value")
        assert redis_client.get("test_key") == "test_value"

        # Cleanup
        redis_client.delete("test_key")

    def test_redis_cache_basic_operations(self, redis_cache):
        """Test basic Redis cache operations."""
        # Test set and get
        redis_cache.set("test_key", "test_value")
        assert redis_cache.get("test_key") == "test_value"

        # Test with JSON data
        test_data = {"name": "test", "value": 123, "nested": {"key": "value"}}
        redis_cache.set("json_key", test_data)
        retrieved_data = redis_cache.get("json_key")
        assert retrieved_data == test_data

        # Test with expiration
        redis_cache.set("expiring_key", "expiring_value", ttl=1)  # 1 second TTL
        assert redis_cache.get("expiring_key") == "expiring_value"

        # Check TTL is set correctly
        ttl = redis_cache.get_ttl("expiring_key")
        assert 0 < ttl <= 1

        # Wait for expiration
        time.sleep(1.5)  # Wait longer than TTL
        assert redis_cache.get("expiring_key") is None

        # Test exists
        redis_cache.set("exists_key", "exists_value")
        assert redis_cache.exists("exists_key") is True
        assert redis_cache.exists("nonexistent_key") is False

        # Test delete
        redis_cache.delete("exists_key")
        assert redis_cache.exists("exists_key") is False

    def test_redis_cache_ttl_operations(self, redis_cache):
        """Test Redis cache TTL operations."""
        # Set key with TTL
        redis_cache.set("ttl_key", "ttl_value", ttl=5)

        # Check TTL
        ttl = redis_cache.get_ttl("ttl_key")
        assert 0 < ttl <= 5

        # Test key without TTL
        redis_cache.set("no_ttl_key", "no_ttl_value")
        ttl = redis_cache.get_ttl("no_ttl_key")
        assert ttl == -1  # No expiration set

        # Test nonexistent key
        ttl = redis_cache.get_ttl("nonexistent_key")
        assert ttl == -2  # Key doesn't exist

    def test_redis_cache_pattern_operations(self, redis_cache):
        """Test Redis cache pattern-based operations."""
        # Set multiple keys with pattern
        redis_cache.set("pattern:key1", "value1")
        redis_cache.set("pattern:key2", "value2")
        redis_cache.set("other:key3", "value3")

        # Clear pattern
        cleared_count = redis_cache.clear_pattern("pattern:*")
        assert cleared_count == 2

        # Verify pattern keys are gone
        assert redis_cache.get("pattern:key1") is None
        assert redis_cache.get("pattern:key2") is None

        # Verify other key still exists
        assert redis_cache.get("other:key3") == "value3"

    def test_redis_cache_stats(self, redis_cache):
        """Test Redis cache statistics."""
        # Set some test data
        redis_cache.set("stats_key1", "value1")
        redis_cache.set("stats_key2", "value2")

        # Get stats
        stats = redis_cache.get_stats()

        # Verify stats structure
        assert "total_keys" in stats
        assert "redis_connected" in stats
        assert "redis_version" in stats
        assert "used_memory" in stats
        assert "connected_clients" in stats

        # Verify stats values
        assert stats["redis_connected"] is True
        assert stats["total_keys"] >= 2  # At least our test keys
        assert isinstance(stats["redis_version"], str)
        assert isinstance(stats["used_memory"], str)
        assert isinstance(stats["connected_clients"], int)

    def test_session_monitor_basic_operations(self, session_monitor):
        """Test basic session monitoring operations."""
        from datetime import datetime, timedelta, timezone

        user_id = str(uuid4())
        session_id = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Track session
        session_monitor.track_session(
            user_id,
            session_id,
            expires_at,
            user_agent="test-agent",
            ip_address="127.0.0.1",
        )

        # Get active sessions
        sessions = session_monitor.get_active_sessions(user_id)
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == session_id

        # Remove session
        session_monitor.remove_session(user_id, session_id)

        # Verify session is gone
        sessions = session_monitor.get_active_sessions(user_id)
        assert len(sessions) == 0

    def test_session_monitor_multiple_sessions(self, session_monitor):
        """Test session monitoring with multiple sessions."""
        from datetime import datetime, timedelta, timezone

        user_id = str(uuid4())
        session1 = str(uuid4())
        session2 = str(uuid4())
        session3 = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Track multiple sessions
        session_monitor.track_session(
            user_id, session1, expires_at, user_agent="desktop"
        )
        session_monitor.track_session(
            user_id, session2, expires_at, user_agent="mobile"
        )
        session_monitor.track_session(
            user_id, session3, expires_at, user_agent="tablet"
        )

        # Get all sessions
        sessions = session_monitor.get_active_sessions(user_id)
        assert len(sessions) == 3

        # Verify session IDs
        session_ids = {s["session_id"] for s in sessions}
        assert session_ids == {session1, session2, session3}

        # Remove one session
        session_monitor.remove_session(user_id, session2)

        # Verify remaining sessions
        sessions = session_monitor.get_active_sessions(user_id)
        assert len(sessions) == 2
        session_ids = {s["session_id"] for s in sessions}
        assert session_ids == {session1, session3}

    def test_session_monitor_logout_all(self, session_monitor):
        """Test logout from all sessions."""
        from datetime import datetime, timedelta, timezone

        user_id = str(uuid4())
        session1 = str(uuid4())
        session2 = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Track multiple sessions
        session_monitor.track_session(
            user_id, session1, expires_at, user_agent="desktop"
        )
        session_monitor.track_session(
            user_id, session2, expires_at, user_agent="mobile"
        )

        # Verify sessions exist
        sessions = session_monitor.get_active_sessions(user_id)
        assert len(sessions) == 2

        # Remove all sessions
        session_monitor.remove_all_sessions(user_id)

        # Verify all sessions are gone
        sessions = session_monitor.get_active_sessions(user_id)
        assert len(sessions) == 0

    def test_token_blacklist_basic_operations(self, token_blacklist):
        """Test basic token blacklisting operations."""
        from datetime import datetime, timedelta, timezone

        token = "test.jwt.token"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Blacklist token
        token_blacklist.blacklist_token(token, expires_at)

        # Check if token is blacklisted
        assert token_blacklist.is_blacklisted(token) is True

        # Note: TokenBlacklist doesn't have a remove method
        # Tokens are automatically removed when they expire

    def test_token_blacklist_expiration(self, token_blacklist):
        """Test token blacklist expiration."""
        from datetime import datetime, timedelta, timezone

        token = "expiring.jwt.token"
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=2)  # 2 second TTL

        # Blacklist token with short TTL
        token_blacklist.blacklist_token(token, expires_at)

        # Verify token is blacklisted
        assert token_blacklist.is_blacklisted(token) is True

        # Wait for expiration
        time.sleep(3.0)  # Wait longer to ensure expiration

        # Clean up expired tokens
        token_blacklist.cleanup_expired()

        # Verify token is no longer blacklisted
        assert token_blacklist.is_blacklisted(token) is False

    def test_token_blacklist_multiple_tokens(self, token_blacklist):
        """Test blacklisting multiple tokens."""
        from datetime import datetime, timedelta, timezone

        token1 = "token1.jwt"
        token2 = "token2.jwt"
        token3 = "token3.jwt"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Blacklist multiple tokens
        token_blacklist.blacklist_token(token1, expires_at)
        token_blacklist.blacklist_token(token2, expires_at)
        token_blacklist.blacklist_token(token3, expires_at)

        # Verify all tokens are blacklisted
        assert token_blacklist.is_blacklisted(token1) is True
        assert token_blacklist.is_blacklisted(token2) is True
        assert token_blacklist.is_blacklisted(token3) is True

        # Verify token hashes
        hash1 = token_blacklist._hash_token(token1)
        hash2 = token_blacklist._hash_token(token2)
        hash3 = token_blacklist._hash_token(token3)

        assert hash1 != hash2 != hash3  # All hashes should be different

    def test_redis_error_handling(self, redis_cache):
        """Test Redis error handling."""
        # Test with invalid key
        assert redis_cache.get("") is None

        # Test with None key
        assert redis_cache.get(None) is None

        # Test with very large value
        large_value = "x" * 1000000  # 1MB string
        redis_cache.set("large_key", large_value)
        retrieved_value = redis_cache.get("large_key")
        assert retrieved_value == large_value

    def test_redis_concurrent_operations(self, redis_cache):
        """Test Redis operations under concurrent access simulation."""
        import threading
        import time

        results = []
        errors = []

        def worker(worker_id: int):
            """Worker function for concurrent testing."""
            try:
                for i in range(10):
                    key = f"concurrent_key_{worker_id}_{i}"
                    value = f"value_{worker_id}_{i}"

                    # Set value
                    redis_cache.set(key, value)

                    # Get value
                    retrieved = redis_cache.get(key)
                    results.append((key, retrieved == value))

                    # Small delay to simulate real usage
                    time.sleep(0.01)

            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all operations succeeded
        assert len(results) == 50  # 5 workers * 10 operations each
        assert all(success for _, success in results), "Some operations failed"

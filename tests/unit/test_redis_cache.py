"""
Test cases for Redis cache service.

This module tests the Redis-based caching functionality.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import redis  # type: ignore

from devcycle.core.cache.redis_cache import RedisCache


class TestRedisCache:
    """Test RedisCache functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for testing."""
        mock_redis = MagicMock(spec=redis.Redis)
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = False
        mock_redis.ttl.return_value = -1
        mock_redis.keys.return_value = []
        mock_redis.info.return_value = {
            "redis_version": "7.0.0",
            "used_memory_human": "1.00M",
            "connected_clients": 1,
        }
        mock_redis.ping.return_value = True
        return mock_redis

    @pytest.fixture
    def redis_cache(self, mock_redis):
        """Create RedisCache instance with mocked Redis."""
        with patch(
            "devcycle.core.cache.redis_cache.redis.Redis", return_value=mock_redis
        ):
            return RedisCache("test:")

    def test_redis_cache_initialization(self, redis_cache):
        """Test RedisCache initialization."""
        assert redis_cache is not None
        assert redis_cache.key_prefix == "test:"

    def test_get_key(self, redis_cache):
        """Test key prefixing."""
        key = redis_cache._get_key("test_key")
        assert key == "test:test_key"

    def test_get_none(self, redis_cache, mock_redis):
        """Test getting non-existent key."""
        mock_redis.get.return_value = None
        result = redis_cache.get("nonexistent")
        assert result is None
        mock_redis.get.assert_called_once_with("test:nonexistent")

    def test_get_string_value(self, redis_cache, mock_redis):
        """Test getting string value."""
        mock_redis.get.return_value = "test_value"
        result = redis_cache.get("test_key")
        assert result == "test_value"

    def test_get_json_value(self, redis_cache, mock_redis):
        """Test getting JSON value."""
        test_data = {"key": "value", "number": 42}
        mock_redis.get.return_value = json.dumps(test_data)
        result = redis_cache.get("test_key")
        assert result == test_data

    def test_set_string_value(self, redis_cache, mock_redis):
        """Test setting string value."""
        result = redis_cache.set("test_key", "test_value")
        assert result is True
        mock_redis.set.assert_called_once_with("test:test_key", "test_value")

    def test_set_json_value(self, redis_cache, mock_redis):
        """Test setting JSON value."""
        test_data = {"key": "value", "number": 42}
        result = redis_cache.set("test_key", test_data)
        assert result is True
        mock_redis.set.assert_called_once_with("test:test_key", json.dumps(test_data))

    def test_set_with_ttl(self, redis_cache, mock_redis):
        """Test setting value with TTL."""
        result = redis_cache.set("test_key", "test_value", ttl=60)
        assert result is True
        mock_redis.setex.assert_called_once_with("test:test_key", 60, "test_value")

    def test_delete(self, redis_cache, mock_redis):
        """Test deleting key."""
        result = redis_cache.delete("test_key")
        assert result is True
        mock_redis.delete.assert_called_once_with("test:test_key")

    def test_exists(self, redis_cache, mock_redis):
        """Test checking key existence."""
        mock_redis.exists.return_value = True
        result = redis_cache.exists("test_key")
        assert result is True
        mock_redis.exists.assert_called_once_with("test:test_key")

    def test_get_ttl(self, redis_cache, mock_redis):
        """Test getting TTL."""
        mock_redis.ttl.return_value = 30
        result = redis_cache.get_ttl("test_key")
        assert result == 30
        mock_redis.ttl.assert_called_once_with("test:test_key")

    def test_clear_pattern(self, redis_cache, mock_redis):
        """Test clearing keys by pattern."""
        mock_redis.keys.return_value = ["test:key1", "test:key2"]
        mock_redis.delete.return_value = 2
        result = redis_cache.clear_pattern("key*")
        assert result == 2
        mock_redis.keys.assert_called_once_with("test:key*")
        mock_redis.delete.assert_called_once_with("test:key1", "test:key2")

    def test_clear_all(self, redis_cache, mock_redis):
        """Test clearing all keys."""
        mock_redis.keys.return_value = ["test:key1", "test:key2"]
        mock_redis.delete.return_value = 2
        result = redis_cache.clear_all()
        assert result == 2
        mock_redis.keys.assert_called_once_with("test:*")

    def test_get_stats(self, redis_cache, mock_redis):
        """Test getting cache statistics."""
        mock_redis.keys.return_value = ["test:key1", "test:key2"]
        stats = redis_cache.get_stats()

        assert stats["total_keys"] == 2
        assert stats["redis_connected"] is True
        assert stats["redis_version"] == "7.0.0"
        assert stats["used_memory"] == "1.00M"
        assert stats["connected_clients"] == 1

    def test_health_check_success(self, redis_cache, mock_redis):
        """Test successful health check."""
        result = redis_cache.health_check()
        assert result is True
        mock_redis.ping.assert_called_once()

    def test_health_check_failure(self, redis_cache, mock_redis):
        """Test failed health check."""
        mock_redis.ping.side_effect = Exception("Connection failed")
        result = redis_cache.health_check()
        assert result is False

    def test_error_handling_get(self, redis_cache, mock_redis):
        """Test error handling in get method."""
        mock_redis.get.side_effect = Exception("Redis error")
        result = redis_cache.get("test_key")
        assert result is None

    def test_error_handling_set(self, redis_cache, mock_redis):
        """Test error handling in set method."""
        mock_redis.set.side_effect = Exception("Redis error")
        result = redis_cache.set("test_key", "test_value")
        assert result is False

    def test_error_handling_delete(self, redis_cache, mock_redis):
        """Test error handling in delete method."""
        mock_redis.delete.side_effect = Exception("Redis error")
        result = redis_cache.delete("test_key")
        assert result is False

    def test_error_handling_stats(self, redis_cache, mock_redis):
        """Test error handling in get_stats method."""
        mock_redis.info.side_effect = Exception("Redis error")
        stats = redis_cache.get_stats()

        assert stats["total_keys"] == 0
        assert stats["redis_connected"] is False
        assert "error" in stats


class TestRedisCacheIntegration:
    """Test Redis cache integration."""

    def test_get_cache_singleton(self):
        """Test that get_cache returns singleton instance."""
        from devcycle.core.cache.redis_cache import get_cache

        cache1 = get_cache("test1:")
        cache2 = get_cache("test2:")

        # Should return the same instance
        assert cache1 is cache2

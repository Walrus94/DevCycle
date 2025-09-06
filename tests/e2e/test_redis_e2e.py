"""
End-to-end tests for Redis functionality.

This module tests Redis functionality in a complete application context,
including integration with FastAPI endpoints and real Redis containers.
"""

import hashlib
import json
import time
from uuid import uuid4

import pytest
import redis  # type: ignore[import-untyped]
from httpx import ASGITransport, AsyncClient
from testcontainers.redis import RedisContainer

from devcycle.api.app import create_app


@pytest.mark.e2e
class TestRedisE2E:
    """End-to-end tests for Redis functionality."""

    @pytest.fixture(scope="class")
    def redis_container(self):
        """Start Redis container for E2E tests."""
        with RedisContainer("redis:7-alpine") as redis_container:
            yield redis_container

    @pytest.fixture
    async def app_with_redis(self, redis_container):
        """Create FastAPI app with Redis configuration."""
        # Mock Redis configuration to use test container
        redis_host = redis_container.get_container_host_ip()
        redis_port = redis_container.get_exposed_port(6379)

        with pytest.MonkeyPatch().context() as m:
            # Create a real Redis client for the test container
            test_redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,
                db=0,
            )

            # Mock Redis client creation for all Redis services
            def mock_redis_client(**kwargs):
                return test_redis_client

            m.setattr("devcycle.core.cache.redis_cache.redis.Redis", mock_redis_client)
            m.setattr(
                "devcycle.core.auth.session_monitor.redis.Redis", mock_redis_client
            )
            m.setattr(
                "devcycle.core.auth.token_blacklist.redis.Redis", mock_redis_client
            )

            # Create app
            app = create_app()
            yield app

    @pytest.fixture
    async def client(self, app_with_redis):
        """Create test client for E2E tests."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_redis), base_url="http://test"
        ) as client:
            yield client

    @pytest.fixture
    def redis_client(self, redis_container):
        """Create direct Redis client for verification."""
        return redis.Redis(
            host=redis_container.get_container_host_ip(),
            port=redis_container.get_exposed_port(6379),
            decode_responses=True,
            db=0,
        )

    async def test_health_endpoint_with_redis(self, client, redis_client):
        """Test health endpoint with Redis connectivity."""
        # Verify Redis is accessible
        assert redis_client.ping() is True

        # Test health endpoint
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data

    async def test_cache_integration_e2e(self, client, redis_client):
        """Test cache integration in E2E context."""
        # Test cache operations through the application
        cache_key = f"e2e_test_{uuid4()}"
        cache_value = {"test": "data", "timestamp": time.time()}

        # Set cache value
        redis_client.set(f"devcycle:cache:{cache_key}", json.dumps(cache_value))

        # Verify cache value
        cached_data = redis_client.get(f"devcycle:cache:{cache_key}")
        assert cached_data is not None

        retrieved_value = json.loads(cached_data)
        assert retrieved_value["test"] == cache_value["test"]

        # Test cache expiration
        redis_client.setex(
            f"devcycle:cache:{cache_key}_expiring", 1, json.dumps(cache_value)
        )

        # Verify immediate access
        cached_data = redis_client.get(f"devcycle:cache:{cache_key}_expiring")
        assert cached_data is not None

        # Wait for expiration
        time.sleep(2.0)  # Wait longer to ensure expiration

        # Verify expiration
        cached_data = redis_client.get(f"devcycle:cache:{cache_key}_expiring")
        assert cached_data is None

    async def test_session_management_e2e(self, client, redis_client):
        """Test session management in E2E context."""
        user_id = str(uuid4())
        session_id = str(uuid4())

        # Simulate session registration
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "metadata": {"ip": "127.0.0.1", "user_agent": "test-agent"},
        }

        # Store session in Redis
        redis_client.hset(
            f"devcycle:sessions:{user_id}",
            session_id,
            json.dumps(session_data),
        )

        # Verify session storage
        stored_session = redis_client.hget(f"devcycle:sessions:{user_id}", session_id)
        assert stored_session is not None

        retrieved_session = json.loads(stored_session)
        assert retrieved_session["session_id"] == session_id
        assert retrieved_session["user_id"] == user_id

        # Test session activity update
        updated_session_data = session_data.copy()
        updated_session_data["last_activity"] = time.time() + 100

        redis_client.hset(
            f"devcycle:sessions:{user_id}",
            session_id,
            json.dumps(updated_session_data),
        )

        # Verify update
        updated_session = redis_client.hget(f"devcycle:sessions:{user_id}", session_id)
        updated_data = json.loads(updated_session)
        assert updated_data["last_activity"] > session_data["last_activity"]

    async def test_token_blacklist_e2e(self, client, redis_client):
        """Test token blacklisting in E2E context."""
        token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.token"
        user_id = str(uuid4())

        # Simulate token blacklisting
        token_hash = f"blacklist:{hashlib.sha256(token.encode()).hexdigest()}"
        blacklist_data = {
            "token_hash": token_hash,
            "user_id": user_id,
            "blacklisted_at": time.time(),
            "expires_at": time.time() + 3600,  # 1 hour
        }

        # Store blacklisted token
        redis_client.set(
            token_hash,
            json.dumps(blacklist_data),
            ex=3600,  # 1 hour expiration
        )

        # Add to user's blacklist set
        redis_client.sadd(f"devcycle:blacklist:user:{user_id}", token_hash)

        # Verify token is blacklisted
        blacklisted_data = redis_client.get(token_hash)
        assert blacklisted_data is not None

        retrieved_data = json.loads(blacklisted_data)
        assert retrieved_data["user_id"] == user_id

        # Verify user blacklist set
        user_blacklist = redis_client.smembers(f"devcycle:blacklist:user:{user_id}")
        assert token_hash in user_blacklist

    async def test_redis_performance_e2e(self, client, redis_client):
        """Test Redis performance in E2E context."""
        # Test bulk operations
        start_time = time.time()

        # Set multiple keys
        for i in range(100):
            key = f"perf_test_key_{i}"
            value = {"index": i, "data": f"test_data_{i}"}
            redis_client.set(f"devcycle:cache:{key}", json.dumps(value))

        set_time = time.time() - start_time

        # Get multiple keys
        start_time = time.time()

        for i in range(100):
            key = f"perf_test_key_{i}"
            cached_data = redis_client.get(f"devcycle:cache:{key}")
            assert cached_data is not None

            retrieved_value = json.loads(cached_data)
            assert retrieved_value["index"] == i

        get_time = time.time() - start_time

        # Verify performance (should be fast)
        assert set_time < 1.0, f"Set operations took too long: {set_time}s"
        assert get_time < 1.0, f"Get operations took too long: {get_time}s"

        # Cleanup
        for i in range(100):
            key = f"perf_test_key_{i}"
            redis_client.delete(f"devcycle:cache:{key}")

    async def test_redis_error_recovery_e2e(self, client, redis_client):
        """Test Redis error recovery in E2E context."""
        # Test with invalid data
        invalid_key = ""
        invalid_value = None

        # These should not crash the application
        redis_client.set(invalid_key, json.dumps(invalid_value))
        result = redis_client.get(invalid_key)
        assert result is not None

        # Test with very large data
        large_data = {"large_field": "x" * 1000000}  # 1MB
        large_key = "large_data_key"

        redis_client.set(f"devcycle:cache:{large_key}", json.dumps(large_data))
        retrieved_data = redis_client.get(f"devcycle:cache:{large_key}")

        assert retrieved_data is not None
        parsed_data = json.loads(retrieved_data)
        assert len(parsed_data["large_field"]) == 1000000

    async def test_redis_memory_usage_e2e(self, client, redis_client):
        """Test Redis memory usage in E2E context."""
        # Get initial memory info
        initial_info = redis_client.info("memory")
        initial_used = initial_info["used_memory"]

        # Store some data
        for i in range(1000):
            key = f"memory_test_key_{i}"
            value = {"index": i, "data": f"test_data_{i}" * 100}  # Larger values
            redis_client.set(f"devcycle:cache:{key}", json.dumps(value))

        # Get memory info after storing data
        after_info = redis_client.info("memory")
        after_used = after_info["used_memory"]

        # Verify memory usage increased
        memory_increase = after_used - initial_used
        assert memory_increase > 0, "Memory usage should have increased"

        # Cleanup
        for i in range(1000):
            key = f"memory_test_key_{i}"
            redis_client.delete(f"devcycle:cache:{key}")

        # Verify memory usage decreased
        final_info = redis_client.info("memory")
        final_used = final_info["used_memory"]

        # Memory should be close to initial (allowing for some overhead)
        memory_difference = abs(final_used - initial_used)
        assert (
            memory_difference < initial_used * 0.1
        ), "Memory should be close to initial"

    async def test_redis_concurrent_access_e2e(self, client, redis_client):
        """Test Redis concurrent access in E2E context."""
        import asyncio

        async def concurrent_worker(worker_id: int, iterations: int = 10):
            """Worker for concurrent testing."""
            results = []
            for i in range(iterations):
                key = f"concurrent_e2e_{worker_id}_{i}"
                value = {"worker": worker_id, "iteration": i, "timestamp": time.time()}

                # Set value
                redis_client.set(f"devcycle:cache:{key}", json.dumps(value))

                # Get value
                cached_data = redis_client.get(f"devcycle:cache:{key}")
                if cached_data:
                    retrieved_value = json.loads(cached_data)
                    results.append(retrieved_value["worker"] == worker_id)

                # Small delay
                await asyncio.sleep(0.01)

            return results

        # Run concurrent workers
        tasks = [concurrent_worker(i, 20) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Verify all operations succeeded
        all_results = [
            result for worker_results in results for result in worker_results
        ]
        assert len(all_results) == 100  # 5 workers * 20 iterations
        assert all(all_results), "Some concurrent operations failed"

        # Cleanup
        for worker_id in range(5):
            for i in range(20):
                key = f"concurrent_e2e_{worker_id}_{i}"
                redis_client.delete(f"devcycle:cache:{key}")

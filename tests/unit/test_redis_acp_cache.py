"""Unit tests for Redis ACP cache integration."""

from unittest.mock import Mock

import pytest

from devcycle.core.cache.acp_cache import ACPCache
from devcycle.core.cache.redis_cache import RedisCache


class TestACPCache:
    """Test ACP cache functionality."""

    @pytest.fixture
    def mock_redis_cache(self):
        """Create a mock Redis cache."""
        mock_cache = Mock(spec=RedisCache)
        mock_cache.key_prefix = "devcycle:cache:"
        mock_cache.redis_client = Mock()
        mock_cache.redis_client.pipeline.return_value = Mock()
        mock_cache.redis_client.smembers.return_value = set()
        mock_cache.redis_client.keys.return_value = []
        mock_cache.redis_client.info.return_value = {
            "keyspace_hits": 100,
            "keyspace_misses": 20,
            "redis_version": "7.0.0",
        }
        mock_cache.clear_pattern = Mock(return_value=10)
        return mock_cache

    @pytest.fixture
    def acp_cache(self, mock_redis_cache):
        """Create ACP cache instance."""
        return ACPCache(mock_redis_cache)

    @pytest.mark.asyncio
    async def test_cache_agent_status(self, acp_cache, mock_redis_cache):
        """Test caching agent status."""
        agent_id = "test-agent-1"
        status = {
            "status": "online",
            "last_seen": "2024-01-01T00:00:00Z",
            "current_runs": 2,
            "max_runs": 5,
        }

        mock_redis_cache.set.return_value = True

        result = await acp_cache.cache_agent_status(agent_id, status)

        assert result is True
        mock_redis_cache.set.assert_called_once_with(
            f"agents:status:{agent_id}", status, ttl=300
        )

    @pytest.mark.asyncio
    async def test_get_agent_status(self, acp_cache, mock_redis_cache):
        """Test getting cached agent status."""
        agent_id = "test-agent-1"
        expected_status = {
            "status": "online",
            "last_seen": "2024-01-01T00:00:00Z",
            "current_runs": 2,
            "max_runs": 5,
        }

        mock_redis_cache.get.return_value = expected_status

        result = await acp_cache.get_agent_status(agent_id)

        assert result == expected_status
        mock_redis_cache.get.assert_called_once_with(f"agents:status:{agent_id}")

    @pytest.mark.asyncio
    async def test_cache_capability_mapping(self, acp_cache, mock_redis_cache):
        """Test caching capability mapping."""
        capability = "code_generation"
        agent_ids = ["agent-1", "agent-2", "agent-3"]

        # Mock pipeline operations
        mock_pipeline = Mock()
        mock_pipeline.delete.return_value = None
        mock_pipeline.sadd.return_value = None
        mock_pipeline.expire.return_value = True
        mock_pipeline.execute.return_value = [None, None, True]
        mock_redis_cache.redis_client.pipeline.return_value = mock_pipeline

        result = await acp_cache.cache_capability_mapping(capability, agent_ids)

        assert result is True
        mock_pipeline.delete.assert_called_once_with(f"capabilities:{capability}")
        mock_pipeline.sadd.assert_called_once_with(
            f"capabilities:{capability}", *agent_ids
        )
        mock_pipeline.expire.assert_called_once_with(f"capabilities:{capability}", 600)

    @pytest.mark.asyncio
    async def test_discover_agents_by_capability(self, acp_cache, mock_redis_cache):
        """Test discovering agents by capability."""
        capability = "code_generation"
        expected_agents = {"agent-1", "agent-2"}

        mock_redis_cache.redis_client.smembers.return_value = expected_agents

        result = await acp_cache.discover_agents_by_capability(capability)

        assert set(result) == expected_agents
        mock_redis_cache.redis_client.smembers.assert_called_once_with(
            f"capabilities:{capability}"
        )

    @pytest.mark.asyncio
    async def test_cache_workflow_state(self, acp_cache, mock_redis_cache):
        """Test caching workflow state."""
        workflow_id = "workflow-123"
        state = {
            "status": "running",
            "current_step": "step-1",
            "progress": 25,
            "started_at": "2024-01-01T00:00:00Z",
        }

        mock_redis_cache.set.return_value = True

        result = await acp_cache.cache_workflow_state(workflow_id, state)

        assert result is True
        mock_redis_cache.set.assert_called_once_with(
            f"workflows:active:{workflow_id}", state, ttl=1800
        )

    @pytest.mark.asyncio
    async def test_get_cache_hit_ratio(self, acp_cache, mock_redis_cache):
        """Test getting cache hit ratio."""
        mock_redis_cache.redis_client.info.return_value = {
            "keyspace_hits": 100,
            "keyspace_misses": 20,
        }

        result = await acp_cache.get_cache_hit_ratio()

        assert result == 100 / 120  # 100 hits / (100 hits + 20 misses)

    @pytest.mark.asyncio
    async def test_get_agent_status_distribution(self, acp_cache, mock_redis_cache):
        """Test getting agent status distribution."""
        mock_redis_cache.redis_client.keys.return_value = [
            "acp:agents:status:agent-1",
            "acp:agents:status:agent-2",
            "acp:agents:status:agent-3",
        ]
        mock_redis_cache.redis_client.hget.side_effect = ["online", "offline", "busy"]

        result = await acp_cache.get_agent_status_distribution()

        assert result == {"online": 1, "offline": 1, "busy": 1}

    @pytest.mark.asyncio
    async def test_batch_update_agent_status(self, acp_cache, mock_redis_cache):
        """Test batch updating agent statuses."""
        agent_updates = [
            {"agent_id": "agent-1", "status": {"status": "online", "runs": 2}},
            {"agent_id": "agent-2", "status": {"status": "offline", "runs": 0}},
        ]

        # Mock pipeline operations
        mock_pipeline = Mock()
        mock_pipeline.hset.return_value = None
        mock_pipeline.expire.return_value = True
        # Each agent has 2 operations (hset + expire), so 4 total results
        # hset returns 1 for success, expire returns True
        mock_pipeline.execute.return_value = [1, True, 1, True]
        mock_redis_cache.redis_client.pipeline.return_value = mock_pipeline

        result = await acp_cache.batch_update_agent_status(agent_updates)

        assert result is True
        assert mock_pipeline.hset.call_count == 2
        assert mock_pipeline.expire.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_agent_cache(self, acp_cache, mock_redis_cache):
        """Test clearing agent cache."""
        agent_id = "test-agent-1"
        mock_redis_cache.redis_client.keys.return_value = [
            "acp:agents:status:test-agent-1",
            "acp:agents:heartbeat:test-agent-1",
            "acp:cache:agents:test-agent-1",
        ]
        mock_redis_cache.redis_client.delete.return_value = 3

        result = await acp_cache.clear_agent_cache(agent_id)

        assert result is True
        mock_redis_cache.redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_all_acp_cache(self, acp_cache, mock_redis_cache):
        """Test clearing all ACP cache."""
        mock_redis_cache.clear_pattern.return_value = 10

        result = await acp_cache.clear_all_acp_cache()

        assert result == 10
        # The method calls _get_key("*") which returns "acp:*",
        # then removes the redis prefix
        mock_redis_cache.clear_pattern.assert_called_once_with("acp:*")

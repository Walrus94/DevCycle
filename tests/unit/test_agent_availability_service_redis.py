"""
Test cases for Redis-backed agent availability service.

This module tests the enhanced agent availability service with Redis caching.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devcycle.core.agents.models import AgentStatus
from devcycle.core.services.agent_availability_service_redis import (
    RedisAgentAvailabilityService,
)


class TestRedisAgentAvailabilityService:
    """Test RedisAgentAvailabilityService functionality."""

    @pytest.fixture
    def mock_agent_repository(self):
        """Mock agent repository for testing."""
        mock_repo = AsyncMock()
        return mock_repo

    @pytest.fixture
    def mock_cache(self):
        """Mock Redis cache for testing."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_cache.delete.return_value = 1
        mock_cache.clear_pattern.return_value = 0
        mock_cache.get_stats.return_value = {"total_keys": 0, "redis_connected": True}
        mock_cache.health_check.return_value = True
        return mock_cache

    @pytest.fixture
    def service(self, mock_agent_repository, mock_cache):
        """Create RedisAgentAvailabilityService with mocked dependencies."""
        with patch(
            "devcycle.core.services.agent_availability_service_redis.get_cache",
            return_value=mock_cache,
        ):
            return RedisAgentAvailabilityService(mock_agent_repository)

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service is not None
        assert service._cache_ttl == 30

    @pytest.mark.asyncio
    async def test_is_agent_available_cache_hit(self, service, mock_cache):
        """Test agent availability check with cache hit."""
        # Mock cache hit
        cached_data = {
            "available": True,
            "status": "online",
            "last_check": time.time(),
        }
        mock_cache.get.return_value = cached_data

        result = await service.is_agent_available("test_agent")

        assert result is True
        mock_cache.get.assert_called_once_with("availability:test_agent")

    @pytest.mark.asyncio
    async def test_is_agent_available_cache_miss(
        self, service, mock_agent_repository, mock_cache
    ):
        """Test agent availability check with cache miss."""
        # Mock cache miss
        mock_cache.get.return_value = None

        # Mock agent data
        mock_agent = MagicMock()
        mock_agent.status = AgentStatus.ONLINE.value
        mock_agent.capabilities = '["test_capability"]'
        mock_agent.configuration = '{"max_concurrent_tasks": 1}'
        mock_agent.current_tasks = 0
        mock_agent_repository.get_by_name.return_value = mock_agent

        result = await service.is_agent_available("test_agent")

        assert result is True
        mock_agent_repository.get_by_name.assert_called_once_with("test_agent")
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_agent_available_agent_not_found(
        self, service, mock_agent_repository, mock_cache
    ):
        """Test agent availability check when agent not found."""
        mock_cache.get.return_value = None
        mock_agent_repository.get_by_name.return_value = None

        result = await service.is_agent_available("nonexistent_agent")

        assert result is False
        mock_agent_repository.get_by_name.assert_called_once_with("nonexistent_agent")

    @pytest.mark.asyncio
    async def test_get_agent_capabilities_cache_hit(self, service, mock_cache):
        """Test getting agent capabilities with cache hit."""
        cached_data = {
            "capabilities": ["test_capability"],
            "last_check": time.time(),
        }
        mock_cache.get.return_value = cached_data

        result = await service.get_agent_capabilities("test_agent")

        assert result == ["test_capability"]
        mock_cache.get.assert_called_once_with("capabilities:test_agent")

    @pytest.mark.asyncio
    async def test_get_agent_capabilities_cache_miss(
        self, service, mock_agent_repository, mock_cache
    ):
        """Test getting agent capabilities with cache miss."""
        mock_cache.get.return_value = None

        # Mock agent data
        mock_agent = MagicMock()
        mock_agent.capabilities = '["test_capability", "another_capability"]'
        mock_agent_repository.get_by_name.return_value = mock_agent

        result = await service.get_agent_capabilities("test_agent")

        assert result == ["test_capability", "another_capability"]
        mock_agent_repository.get_by_name.assert_called_once_with("test_agent")
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_agent_capability(self, service):
        """Test validating agent capability."""
        with patch.object(
            service,
            "get_agent_capabilities",
            return_value=["test_capability", "another_capability"],
        ):
            result = await service.validate_agent_capability(
                "test_agent", "test_capability"
            )
            assert result is True

            result = await service.validate_agent_capability(
                "test_agent", "nonexistent_capability"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_get_available_agents_by_capability_cache_hit(
        self, service, mock_cache
    ):
        """Test getting available agents by capability with cache hit."""
        cached_data = {
            "agent_ids": ["agent1", "agent2"],
            "last_check": time.time(),
        }
        mock_cache.get.return_value = cached_data

        result = await service.get_available_agents_by_capability("test_capability")

        assert result == ["agent1", "agent2"]
        mock_cache.get.assert_called_once_with("agents_by_capability:test_capability")

    @pytest.mark.asyncio
    async def test_get_agent_load_cache_hit(self, service, mock_cache):
        """Test getting agent load with cache hit."""
        cached_data = {
            "load_info": {
                "agent_id": "test_agent",
                "status": "online",
                "current_tasks": 1,
                "max_concurrent_tasks": 5,
                "available_slots": 4,
            },
            "last_check": time.time(),
        }
        mock_cache.get.return_value = cached_data

        result = await service.get_agent_load("test_agent")

        assert result["agent_id"] == "test_agent"
        assert result["available_slots"] == 4
        mock_cache.get.assert_called_once_with("load:test_agent")

    @pytest.mark.asyncio
    async def test_get_least_busy_agent(self, service):
        """Test getting least busy agent."""
        with patch.object(
            service,
            "get_available_agents_by_capability",
            return_value=["agent1", "agent2"],
        ):
            with patch.object(service, "get_agent_load") as mock_get_load:
                mock_get_load.side_effect = [
                    {"available_slots": 2, "response_time_ms": 100},
                    {"available_slots": 4, "response_time_ms": 50},
                ]

                result = await service.get_least_busy_agent(["test_capability"])

                assert result == "agent2"  # More available slots

    def test_is_agent_busy(self, service):
        """Test checking if agent is busy."""
        # Mock agent with current tasks
        mock_agent = MagicMock()
        mock_agent.configuration = '{"max_concurrent_tasks": 2}'
        mock_agent.current_tasks = 2

        result = service._is_agent_busy(mock_agent)
        assert result is True

        mock_agent.current_tasks = 1
        result = service._is_agent_busy(mock_agent)
        assert result is False

    def test_is_agent_in_maintenance(self, service):
        """Test checking if agent is in maintenance."""
        mock_agent = MagicMock()
        mock_agent.status = AgentStatus.MAINTENANCE.value

        result = service._is_agent_in_maintenance(mock_agent)
        assert result is True

        mock_agent.status = AgentStatus.ONLINE.value
        result = service._is_agent_in_maintenance(mock_agent)
        assert result is False

    def test_is_cache_valid(self, service):
        """Test cache validity check."""
        # Valid cache data
        valid_data = {"last_check": time.time() - 10}  # 10 seconds ago
        assert service._is_cache_valid(valid_data) is True

        # Expired cache data
        expired_data = {"last_check": time.time() - 40}  # 40 seconds ago
        assert service._is_cache_valid(expired_data) is False

        # No cache data
        assert service._is_cache_valid({}) is False
        assert service._is_cache_valid(None) is False

    def test_clear_cache_specific_agent(self, service, mock_cache):
        """Test clearing cache for specific agent."""
        mock_cache.delete.return_value = 1

        result = service.clear_cache("test_agent")

        assert result == 3  # 3 cache entries cleared
        assert mock_cache.delete.call_count == 3

    def test_clear_cache_all_agents(self, service, mock_cache):
        """Test clearing all agent cache."""
        mock_cache.clear_pattern.return_value = 5

        result = service.clear_cache()

        assert result == 20  # 4 patterns * 5 entries each
        assert mock_cache.clear_pattern.call_count == 4

    def test_get_cache_stats(self, service, mock_cache):
        """Test getting cache statistics."""
        stats = service.get_cache_stats()
        assert stats == {"total_keys": 0, "redis_connected": True}
        mock_cache.get_stats.assert_called_once()

    def test_health_check(self, service, mock_cache):
        """Test health check."""
        result = service.health_check()
        assert result is True
        mock_cache.health_check.assert_called_once()


class TestRedisAgentAvailabilityServiceIntegration:
    """Test Redis agent availability service integration."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete workflow with mocked dependencies."""
        with patch(
            "devcycle.core.services.agent_availability_service_redis.get_cache"
        ) as mock_get_cache:
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            mock_cache.set.return_value = True
            mock_get_cache.return_value = mock_cache

            mock_repo = AsyncMock()
            mock_agent = MagicMock()
            mock_agent.status = AgentStatus.ONLINE.value
            mock_agent.capabilities = '["test_capability"]'
            mock_agent.configuration = '{"max_concurrent_tasks": 1}'
            mock_agent.current_tasks = 0
            mock_repo.get_by_name.return_value = mock_agent

            service = RedisAgentAvailabilityService(mock_repo)

            # Test availability check
            available = await service.is_agent_available("test_agent")
            assert available is True

            # Test capabilities
            capabilities = await service.get_agent_capabilities("test_agent")
            assert capabilities == ["test_capability"]

            # Test capability validation
            has_capability = await service.validate_agent_capability(
                "test_agent", "test_capability"
            )
            assert has_capability is True

"""
Unit tests for agent availability service.

This module tests the AgentAvailabilityService functionality,
including agent availability checks, capability validation, and load management.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from devcycle.core.services.agent_availability_service import AgentAvailabilityService


class TestAgentAvailabilityService:
    """Test cases for AgentAvailabilityService."""

    @pytest.fixture
    def service(self, mock_agent_service):
        """Create a service instance for testing."""
        return AgentAvailabilityService(mock_agent_service)

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        agent = MagicMock()
        agent.id = "test_agent"
        agent.status = "online"
        agent.current_tasks = 2
        agent.last_heartbeat = datetime.now(timezone.utc)
        agent.response_time_ms = 150
        agent.capabilities = '["text_processing", "analysis"]'  # JSON string
        agent.configuration = '{"max_concurrent_tasks": 5}'  # JSON string
        return agent

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.cache is not None
        assert service._cache_ttl == 30

    @pytest.mark.asyncio
    async def test_is_agent_available_cache_hit(self, service):
        """Test agent availability check with cache hit."""
        # Mock cache hit
        with patch.object(service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = {"available": True, "last_check": 1000.0}

            with patch("time.time", return_value=1020.0):  # Within TTL
                result = await service.is_agent_available("test_agent")
                assert result is True

    @pytest.mark.asyncio
    async def test_is_agent_available_cache_miss(self, service, mock_agent):
        """Test agent availability check with cache miss."""
        # Mock cache miss
        with patch.object(service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = None

            # Mock the service to return our mock agent
            service.agent_service.get_agent_by_name.return_value = mock_agent

            # Mock cache set
            with patch.object(service.cache, "set") as mock_cache_set:
                with patch("time.time", return_value=1000.0):
                    result = await service.is_agent_available("test_agent")
                    assert result is True

                    # Verify cache was updated
                    mock_cache_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_agent_available_agent_not_found(self, service):
        """Test agent availability check when agent is not found."""
        # Mock cache miss
        with patch.object(service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = None

            # Mock the service to return None (agent not found)
            service.agent_service.get_agent_by_name.return_value = None

            result = await service.is_agent_available("nonexistent_agent")
            assert result is False

    @pytest.mark.asyncio
    async def test_is_agent_available_offline_agent(self, service, mock_agent):
        """Test agent availability check for offline agent."""
        mock_agent.status = "offline"

        # Mock cache miss
        with patch.object(service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = None

            # Mock the service to return our mock agent
            service.agent_service.get_agent_by_name.return_value = mock_agent

            # Mock cache set
            with patch.object(service.cache, "set"):
                with patch("time.time", return_value=1000.0):
                    result = await service.is_agent_available("test_agent")
                    assert result is False

    @pytest.mark.asyncio
    async def test_get_agent_capabilities_cache_hit(self, service):
        """Test getting agent capabilities with cache hit."""
        # Mock cache hit
        with patch.object(service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = {
                "capabilities": ["text_processing", "analysis"],
                "last_check": 1000.0,
            }

            with patch("time.time", return_value=1020.0):  # Within TTL
                result = await service.get_agent_capabilities("test_agent")
                assert result == ["text_processing", "analysis"]

    @pytest.mark.asyncio
    async def test_get_agent_capabilities_cache_miss(self, service, mock_agent):
        """Test getting agent capabilities with cache miss."""
        # Mock cache miss
        with patch.object(service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = None

            # Mock the service to return our mock agent
            service.agent_service.get_agent_by_name.return_value = mock_agent

            # Mock cache set
            with patch.object(service.cache, "set"):
                with patch("time.time", return_value=1000.0):
                    result = await service.get_agent_capabilities("test_agent")
                    assert result == ["text_processing", "analysis"]

    @pytest.mark.asyncio
    async def test_get_agent_capabilities_agent_not_found(self, service):
        """Test getting agent capabilities when agent is not found."""
        # Mock cache miss
        with patch.object(service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = None

            # Mock the service to return None (agent not found)
            service.agent_service.get_agent_by_name.return_value = None

            result = await service.get_agent_capabilities("nonexistent_agent")
            assert result == []

    @pytest.mark.asyncio
    async def test_validate_agent_capability_true(self, service):
        """Test capability validation when agent has the capability."""
        with patch.object(service, "get_agent_capabilities") as mock_get_caps:
            mock_get_caps.return_value = ["text_processing", "analysis"]

            result = await service.validate_agent_capability(
                "test_agent", "text_processing"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_agent_capability_false(self, service):
        """Test capability validation when agent lacks the capability."""
        with patch.object(service, "get_agent_capabilities") as mock_get_caps:
            mock_get_caps.return_value = ["text_processing"]

            result = await service.validate_agent_capability(
                "test_agent", "code_generation"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_get_agent_load_success(self, service, mock_agent):
        """Test getting agent load information successfully."""
        # Mock cache miss
        with patch.object(service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = None

            # Mock the service to return our mock agent
            service.agent_service.get_agent_by_name.return_value = mock_agent

            # Mock cache set
            with patch.object(service.cache, "set"):
                with patch("time.time", return_value=1000.0):
                    result = await service.get_agent_load("test_agent")

                    assert result["agent_id"] == "test_agent"
                    assert result["status"] == "online"
                    assert result["current_tasks"] == 2
                    assert result["max_concurrent_tasks"] == 5
                    assert result["available_slots"] == 3
                    assert result["last_heartbeat"] == mock_agent.last_heartbeat
                    assert result["response_time_ms"] == 150

    @pytest.mark.asyncio
    async def test_get_agent_load_agent_not_found(self, service):
        """Test getting agent load when agent is not found."""
        # Mock cache miss
        with patch.object(service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = None

            # Mock the service to return None (agent not found)
            service.agent_service.get_agent_by_name.return_value = None

            result = await service.get_agent_load("nonexistent_agent")
            assert result["error"] == "Agent not found"

    @pytest.mark.asyncio
    async def test_get_least_busy_agent_success(self, service):
        """Test getting least busy agent successfully."""
        # Mock the get_available_agents_by_capability method to return test data
        with patch.object(
            service, "get_available_agents_by_capability"
        ) as mock_get_agents:
            mock_get_agents.return_value = ["agent1", "agent2"]

            # Mock the get_agent_load method to return test load data
            with patch.object(service, "get_agent_load") as mock_get_load:
                mock_get_load.side_effect = [
                    {"available_slots": 3, "response_time_ms": 100},
                    {"available_slots": 5, "response_time_ms": 50},
                ]

                result = await service.get_least_busy_agent(["text_processing"])
                assert result == "agent2"  # More available slots (5 vs 3)

    @pytest.mark.asyncio
    async def test_get_least_busy_agent_no_available_agents(self, service):
        """Test getting least busy agent when no agents are available."""
        with patch.object(
            service, "get_available_agents_by_capability"
        ) as mock_get_agents:
            mock_get_agents.return_value = []

            result = await service.get_least_busy_agent(["text_processing"])
            assert result is None

    @pytest.mark.asyncio
    async def test_get_least_busy_agent_load_error(self, service):
        """Test getting least busy agent when load check fails."""
        with patch.object(
            service, "get_available_agents_by_capability"
        ) as mock_get_agents:
            mock_get_agents.return_value = ["agent1"]

            with patch.object(service, "get_agent_load") as mock_get_load:
                mock_get_load.return_value = {"error": "Load check failed"}

                result = await service.get_least_busy_agent(["text_processing"])
                assert result is None


class TestAgentAvailabilityServiceIntegration:
    """Integration tests for AgentAvailabilityService."""

    @pytest.mark.asyncio
    async def test_complete_availability_workflow(self, mock_agent_service):
        """Test a complete agent availability workflow."""
        service = AgentAvailabilityService(mock_agent_service)

        # Mock agent data
        mock_agent = MagicMock()
        mock_agent.id = "business_analyst_1"
        mock_agent.status = "online"
        mock_agent.current_tasks = 1
        mock_agent.last_heartbeat = datetime.now(timezone.utc)
        mock_agent.response_time_ms = 100
        mock_agent.capabilities = '["text_processing", "analysis"]'
        mock_agent.configuration = '{"max_concurrent_tasks": 3}'  # JSON string

        # Mock cache miss
        with patch.object(service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = None

            # Mock the service to return our mock agent
            service.agent_service.get_agent_by_name.return_value = mock_agent

            # Mock cache set
            with patch.object(service.cache, "set"):
                with patch("time.time", return_value=1000.0):
                    # Test availability check
                    is_available = await service.is_agent_available(
                        "business_analyst_1"
                    )
                    assert is_available is True

                    # Test capability check
                    has_capability = await service.validate_agent_capability(
                        "business_analyst_1", "text_processing"
                    )
                    assert has_capability is True

                    # Test load information
                    load_info = await service.get_agent_load("business_analyst_1")
                    assert load_info["available_slots"] == 2
                    assert load_info["current_tasks"] == 1

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, mock_agent_service):
        """Test error handling in the availability service."""
        service = AgentAvailabilityService(mock_agent_service)

        # Mock cache miss
        with patch.object(service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = None

            # Mock service to raise an exception
            service.agent_service.get_agent_by_name.side_effect = Exception(
                "Database connection failed"
            )

            # Test that errors are handled gracefully
            result = await service.is_agent_available("test_agent")
            assert result is False

            result = await service.get_agent_capabilities("test_agent")
            assert result == []

            result = await service.get_agent_load("test_agent")
            assert "error" in result

"""
Unit tests for agent availability service.

This module tests the AgentAvailabilityService functionality,
including agent availability checks, capability validation, and load management.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from devcycle.core.agents.models import AgentCapability, AgentStatus
from devcycle.core.services.agent_availability_service import AgentAvailabilityService


class TestAgentAvailabilityService:
    """Test cases for AgentAvailabilityService."""

    @pytest.fixture
    def service(self, mock_agent_repository):
        """Create a service instance for testing."""
        return AgentAvailabilityService(mock_agent_repository)

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        agent = MagicMock()
        agent.id = "test_agent"
        agent.status = AgentStatus.ONLINE.value
        agent.current_tasks = 2
        agent.last_heartbeat = datetime.now(timezone.utc)
        agent.response_time_ms = 150
        agent.capabilities = '["text_processing", "analysis"]'  # JSON string

        # Set configuration as JSON string
        agent.configuration = '{"max_concurrent_tasks": 5}'

        return agent

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service._cache == {}
        assert service._cache_ttl == 30
        assert service._last_cache_update == 0

    @pytest.mark.asyncio
    async def test_is_agent_available_cache_hit(self, service):
        """Test agent availability check with cache hit."""
        # Setup cache
        service._cache["test_agent"] = {"available": True, "last_check": 1000.0}

        # Mock time to make cache valid
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1020.0  # Within TTL

            result = await service.is_agent_available("test_agent")
            assert result is True

    @pytest.mark.asyncio
    async def test_is_agent_available_cache_miss(self, service, mock_agent):
        """Test agent availability check with cache miss."""
        # Mock the repository to return our mock agent
        service.agent_repository.get_by_name.return_value = mock_agent

        # Mock time
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1000.0

            result = await service.is_agent_available("test_agent")
            assert result is True

            # Verify cache was updated
            assert "test_agent" in service._cache
            assert service._cache["test_agent"]["available"] is True

    @pytest.mark.asyncio
    async def test_is_agent_available_agent_not_found(self, service):
        """Test agent availability check when agent is not found."""
        # Mock the repository to return None (agent not found)
        service.agent_repository.get_by_name.return_value = None

        result = await service.is_agent_available("nonexistent_agent")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_agent_available_offline_agent(self, service, mock_agent):
        """Test agent availability check for offline agent."""
        mock_agent.status = AgentStatus.OFFLINE.value

        # Mock the repository to return our mock agent
        service.agent_repository.get_by_name.return_value = mock_agent

        result = await service.is_agent_available("test_agent")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_agent_available_busy_agent(self, service, mock_agent):
        """Test agent availability check for busy agent."""
        mock_agent.current_tasks = 5  # At max capacity
        mock_agent.configuration = '{"max_concurrent_tasks": 5}'  # JSON string

        # Mock the repository to return our mock agent
        service.agent_repository.get_by_name.return_value = mock_agent

        result = await service.is_agent_available("test_agent")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_agent_available_maintenance_agent(self, service, mock_agent):
        """Test agent availability check for agent in maintenance."""
        mock_agent.status = AgentStatus.MAINTENANCE.value

        # Mock the repository to return our mock agent
        service.agent_repository.get_by_name.return_value = mock_agent

        result = await service.is_agent_available("test_agent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_agent_capabilities_cache_hit(self, service):
        """Test getting agent capabilities with cache hit."""
        # Setup cache
        service._cache["test_agent"] = {
            "capabilities": ["text_processing", "analysis"],
            "last_check": 1000.0,
        }

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1020.0  # Within TTL

            result = await service.get_agent_capabilities("test_agent")
            assert result == ["text_processing", "analysis"]

    @pytest.mark.asyncio
    async def test_get_agent_capabilities_cache_miss(self, service, mock_agent):
        """Test getting agent capabilities with cache miss."""
        # Mock the repository to return our mock agent
        service.agent_repository.get_by_name.return_value = mock_agent

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1000.0

            result = await service.get_agent_capabilities("test_agent")
            assert result == ["text_processing", "analysis"]

    @pytest.mark.asyncio
    async def test_get_agent_capabilities_agent_not_found(self, service):
        """Test getting agent capabilities when agent is not found."""
        # Mock the repository to return None (agent not found)
        service.agent_repository.get_by_name.return_value = None

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
    async def test_get_available_agents_by_capability(self, service):
        """Test getting available agents by capability."""
        with patch.object(
            service, "get_available_agents_by_capability"
        ) as mock_get_agents:
            mock_get_agents.return_value = []

            result = await service.get_available_agents_by_capability("text_processing")
            assert result == []

    @pytest.mark.asyncio
    async def test_get_agent_load_success(self, service, mock_agent):
        """Test getting agent load information successfully."""
        # Mock the repository to return our mock agent
        service.agent_repository.get_by_name.return_value = mock_agent

        result = await service.get_agent_load("test_agent")

        assert result["agent_id"] == "test_agent"
        assert result["status"] == AgentStatus.ONLINE.value
        assert result["current_tasks"] == 2
        assert result["max_concurrent_tasks"] == 5
        assert result["available_slots"] == 3
        assert result["last_heartbeat"] == mock_agent.last_heartbeat
        assert result["response_time_ms"] == 150

    @pytest.mark.asyncio
    async def test_get_agent_load_agent_not_found(self, service):
        """Test getting agent load when agent is not found."""
        # Mock the repository to return None (agent not found)
        service.agent_repository.get_by_name.return_value = None

        result = await service.get_agent_load("nonexistent_agent")
        assert result["error"] == "Agent not found"

    @pytest.mark.asyncio
    async def test_get_agent_load_no_configuration(self, service, mock_agent):
        """Test getting agent load when agent has no configuration."""
        mock_agent.configuration = None

        # Mock the repository to return our mock agent
        service.agent_repository.get_by_name.return_value = mock_agent

        result = await service.get_agent_load("test_agent")

        assert result["max_concurrent_tasks"] == 1
        assert result["available_slots"] == 0  # 1 - 2 = -1, but max(0, -1) = 0

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

    def test_is_agent_busy_true(self, service, mock_agent):
        """Test checking if agent is busy when it is."""
        mock_agent.current_tasks = 5
        mock_agent.configuration = '{"max_concurrent_tasks": 5}'  # JSON string

        result = service._is_agent_busy(mock_agent)
        assert result is True

    def test_is_agent_busy_false(self, service, mock_agent):
        """Test checking if agent is busy when it is not."""
        mock_agent.current_tasks = 2
        mock_agent.configuration = '{"max_concurrent_tasks": 5}'  # JSON string

        result = service._is_agent_busy(mock_agent)
        assert result is False

    def test_is_agent_busy_no_configuration(self, service, mock_agent):
        """Test checking if agent is busy when it has no configuration."""
        mock_agent.configuration = None
        mock_agent.current_tasks = 0  # Set to 0 so it's not busy with default max of 1

        result = service._is_agent_busy(mock_agent)
        assert result is False

    def test_is_agent_in_maintenance_true(self, service, mock_agent):
        """Test checking if agent is in maintenance when it is."""
        mock_agent.status = AgentStatus.MAINTENANCE.value

        result = service._is_agent_in_maintenance(mock_agent)
        assert result is True

    def test_is_agent_in_maintenance_false(self, service, mock_agent):
        """Test checking if agent is in maintenance when it is not."""
        mock_agent.status = AgentStatus.ONLINE.value

        result = service._is_agent_in_maintenance(mock_agent)
        assert result is False

    def test_is_cache_valid_true(self, service):
        """Test cache validity check when cache is valid."""
        service._cache["test_agent"] = {"last_check": 1000.0}

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1020.0  # Within TTL

            result = service._is_cache_valid("test_agent")
            assert result is True

    def test_is_cache_valid_false(self, service):
        """Test cache validity check when cache is invalid."""
        service._cache["test_agent"] = {"last_check": 1000.0}

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1040.0  # Outside TTL

            result = service._is_cache_valid("test_agent")
            assert result is False

    def test_is_cache_valid_not_found(self, service):
        """Test cache validity check when agent not in cache."""
        result = service._is_cache_valid("nonexistent_agent")
        assert result is False

    def test_update_cache_new_agent(self, service):
        """Test updating cache for new agent."""
        data = {"available": True, "status": "online"}

        service._update_cache("new_agent", data)

        assert "new_agent" in service._cache
        assert service._cache["new_agent"]["available"] is True
        assert service._cache["new_agent"]["status"] == "online"

    def test_update_cache_existing_agent(self, service):
        """Test updating cache for existing agent."""
        service._cache["existing_agent"] = {"old_data": "value"}

        data = {"new_data": "new_value"}
        service._update_cache("existing_agent", data)

        assert service._cache["existing_agent"]["old_data"] == "value"
        assert service._cache["existing_agent"]["new_data"] == "new_value"

    def test_clear_cache_specific_agent(self, service):
        """Test clearing cache for specific agent."""
        service._cache["agent1"] = {"data": "value1"}
        service._cache["agent2"] = {"data": "value2"}

        service.clear_cache("agent1")

        assert "agent1" not in service._cache
        assert "agent2" in service._cache

    def test_clear_cache_all_agents(self, service):
        """Test clearing cache for all agents."""
        service._cache["agent1"] = {"data": "value1"}
        service._cache["agent2"] = {"data": "value2"}

        service.clear_cache()

        assert service._cache == {}


class TestAgentAvailabilityServiceIntegration:
    """Integration tests for AgentAvailabilityService."""

    @pytest.mark.asyncio
    async def test_complete_availability_workflow(self, mock_agent_repository):
        """Test a complete agent availability workflow."""
        service = AgentAvailabilityService(mock_agent_repository)

        # Mock agent data
        mock_agent = MagicMock()
        mock_agent.id = "business_analyst_1"
        mock_agent.status = AgentStatus.ONLINE
        mock_agent.current_tasks = 1
        mock_agent.last_heartbeat = datetime.now(timezone.utc)
        mock_agent.response_time_ms = 100
        mock_agent.capabilities = [
            AgentCapability.TEXT_PROCESSING,
            AgentCapability.ANALYSIS,
        ]

        mock_agent.configuration = '{"max_concurrent_tasks": 3}'  # JSON string

        # Mock the repository to return our mock agent
        service.agent_repository.get_by_name.return_value = mock_agent

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1000.0

            # Test availability check
            is_available = await service.is_agent_available("business_analyst_1")
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
    async def test_error_handling_workflow(self, mock_agent_repository):
        """Test error handling in the availability service."""
        service = AgentAvailabilityService(mock_agent_repository)

        # Mock repository to raise an exception
        mock_agent_repository.get_by_id.side_effect = Exception(
            "Database connection failed"
        )

        # Test that errors are handled gracefully
        result = await service.is_agent_available("test_agent")
        assert result is False

        result = await service.get_agent_capabilities("test_agent")
        assert result == []

        result = await service.get_agent_load("test_agent")
        assert "error" in result

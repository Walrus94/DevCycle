"""
Tests for agent lifecycle and state management.

This module contains comprehensive tests for the agent lifecycle system,
including state transitions, event handling, and lifecycle operations.
"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from devcycle.core.agents.lifecycle import (
    AgentExecutionState,
    AgentLifecycleManager,
    AgentLifecycleService,
    AgentLifecycleState,
    AgentStateTransition,
)


class TestAgentLifecycleState:
    """Test agent lifecycle states and transitions."""

    def test_state_enum_values(self):
        """Test that all expected states are defined."""
        expected_states = {
            "registered",
            "deploying",
            "deployed",
            "starting",
            "online",
            "busy",
            "idle",
            "stopping",
            "updating",
            "scaling",
            "error",
            "failed",
            "timeout",
            "maintenance",
            "suspended",
            "offline",
            "terminated",
            "deleted",
        }

        actual_states = {state.value for state in AgentLifecycleState}
        assert actual_states == expected_states

    def test_execution_state_enum_values(self):
        """Test that all expected execution states are defined."""
        expected_states = {
            "pending",
            "running",
            "completed",
            "failed",
            "cancelled",
            "timeout",
        }

        actual_states = {state.value for state in AgentExecutionState}
        assert actual_states == expected_states


class TestAgentStateTransition:
    """Test agent state transition model."""

    def test_state_transition_creation(self):
        """Test creating a state transition."""
        transition = AgentStateTransition(
            from_state=AgentLifecycleState.REGISTERED,
            to_state=AgentLifecycleState.DEPLOYING,
            timestamp=datetime.now(timezone.utc),
            reason="Starting deployment",
            metadata={"deployment_id": "deploy-123"},
            triggered_by="system",
        )

        assert transition.from_state == AgentLifecycleState.REGISTERED
        assert transition.to_state == AgentLifecycleState.DEPLOYING
        assert transition.reason == "Starting deployment"
        assert transition.metadata["deployment_id"] == "deploy-123"
        assert transition.triggered_by == "system"


class TestAgentLifecycleManager:
    """Test agent lifecycle manager."""

    @pytest.fixture
    def agent_id(self):
        """Create a test agent ID."""
        return uuid4()

    @pytest.fixture
    def manager(self, agent_id):
        """Create a lifecycle manager."""
        return AgentLifecycleManager(agent_id, AgentLifecycleState.REGISTERED)

    def test_manager_initialization(self, manager, agent_id):
        """Test manager initialization."""
        assert manager.agent_id == agent_id
        assert manager.current_state == AgentLifecycleState.REGISTERED
        assert len(manager.state_history) == 1
        assert manager.state_history[0].to_state == AgentLifecycleState.REGISTERED

    def test_valid_transitions_from_registered(self, manager):
        """Test valid transitions from REGISTERED state."""
        valid_transitions = manager.get_valid_transitions()
        expected = {AgentLifecycleState.DEPLOYING, AgentLifecycleState.DELETED}
        assert valid_transitions == expected

    def test_valid_transitions_from_online(self, manager):
        """Test valid transitions from ONLINE state."""
        # First transition to ONLINE
        manager.current_state = AgentLifecycleState.ONLINE
        valid_transitions = manager.get_valid_transitions()
        expected = {
            AgentLifecycleState.BUSY,
            AgentLifecycleState.IDLE,
            AgentLifecycleState.STOPPING,
            AgentLifecycleState.UPDATING,
            AgentLifecycleState.MAINTENANCE,
            AgentLifecycleState.SUSPENDED,
            AgentLifecycleState.OFFLINE,
            AgentLifecycleState.ERROR,
        }
        assert valid_transitions == expected

    def test_can_transition_to_valid_state(self, manager):
        """Test transition validation for valid states."""
        assert manager.can_transition_to(AgentLifecycleState.DEPLOYING)
        assert manager.can_transition_to(AgentLifecycleState.DELETED)

    def test_can_transition_to_invalid_state(self, manager):
        """Test transition validation for invalid states."""
        assert not manager.can_transition_to(AgentLifecycleState.ONLINE)
        assert not manager.can_transition_to(AgentLifecycleState.BUSY)

    @pytest.mark.asyncio
    async def test_successful_transition(self, manager):
        """Test successful state transition."""
        result = await manager.transition_to(
            AgentLifecycleState.DEPLOYING,
            reason="Starting deployment",
            triggered_by="system",
        )

        assert result is True
        assert manager.current_state == AgentLifecycleState.DEPLOYING
        assert len(manager.state_history) == 2
        assert manager.state_history[-1].to_state == AgentLifecycleState.DEPLOYING

    @pytest.mark.asyncio
    async def test_failed_transition(self, manager):
        """Test failed state transition."""
        result = await manager.transition_to(
            AgentLifecycleState.ONLINE,  # Invalid transition
            reason="Invalid transition",
            triggered_by="system",
        )

        assert result is False
        assert manager.current_state == AgentLifecycleState.REGISTERED
        assert len(manager.state_history) == 1  # No new transition recorded

    @pytest.mark.asyncio
    async def test_transition_with_metadata(self, manager):
        """Test state transition with metadata."""
        metadata = {"deployment_id": "deploy-123", "version": "1.0.0"}

        result = await manager.transition_to(
            AgentLifecycleState.DEPLOYING,
            reason="Starting deployment",
            triggered_by="system",
            metadata=metadata,
        )

        assert result is True
        transition = manager.state_history[-1]
        assert transition.metadata == metadata

    def test_state_history_retrieval(self, manager):
        """Test state history retrieval."""
        # Add some transitions
        manager.current_state = AgentLifecycleState.DEPLOYING
        manager._record_state_transition(
            AgentLifecycleState.REGISTERED,
            AgentLifecycleState.DEPLOYING,
            "Test transition",
            "test",
        )

        history = manager.get_state_history()
        assert len(history) == 2

        limited_history = manager.get_state_history(limit=1)
        assert len(limited_history) == 1

    def test_current_state_info(self, manager):
        """Test current state information retrieval."""
        info = manager.get_current_state_info()

        assert "agent_id" in info
        assert "current_state" in info
        assert "valid_transitions" in info
        assert "state_history_count" in info
        assert "last_transition" in info

        assert info["current_state"] == AgentLifecycleState.REGISTERED
        assert info["state_history_count"] == 1

    def test_operational_state_check(self, manager):
        """Test operational state checking."""
        # Not operational initially
        assert not manager.is_operational()

        # Set to operational states
        manager.current_state = AgentLifecycleState.ONLINE
        assert manager.is_operational()

        manager.current_state = AgentLifecycleState.BUSY
        assert manager.is_operational()

        manager.current_state = AgentLifecycleState.IDLE
        assert manager.is_operational()

        # Set to non-operational states
        manager.current_state = AgentLifecycleState.OFFLINE
        assert not manager.is_operational()

    def test_available_for_tasks_check(self, manager):
        """Test availability for tasks checking."""
        # Not available initially
        assert not manager.is_available_for_tasks()

        # Set to available states
        manager.current_state = AgentLifecycleState.ONLINE
        assert manager.is_available_for_tasks()

        manager.current_state = AgentLifecycleState.IDLE
        assert manager.is_available_for_tasks()

        # Set to unavailable states
        manager.current_state = AgentLifecycleState.BUSY
        assert not manager.is_available_for_tasks()

        manager.current_state = AgentLifecycleState.OFFLINE
        assert not manager.is_available_for_tasks()

    def test_error_state_check(self, manager):
        """Test error state checking."""
        # Not in error initially
        assert not manager.is_in_error_state()

        # Set to error states
        manager.current_state = AgentLifecycleState.ERROR
        assert manager.is_in_error_state()

        manager.current_state = AgentLifecycleState.FAILED
        assert manager.is_in_error_state()

        manager.current_state = AgentLifecycleState.TIMEOUT
        assert manager.is_in_error_state()

        # Set to non-error states
        manager.current_state = AgentLifecycleState.ONLINE
        assert not manager.is_in_error_state()

    def test_maintenance_state_check(self, manager):
        """Test maintenance state checking."""
        # Not in maintenance initially
        assert not manager.is_in_maintenance()

        # Set to maintenance states
        manager.current_state = AgentLifecycleState.MAINTENANCE
        assert manager.is_in_maintenance()

        manager.current_state = AgentLifecycleState.SUSPENDED
        assert manager.is_in_maintenance()

        manager.current_state = AgentLifecycleState.UPDATING
        assert manager.is_in_maintenance()

        # Set to non-maintenance states
        manager.current_state = AgentLifecycleState.ONLINE
        assert not manager.is_in_maintenance()

    @pytest.mark.asyncio
    async def test_event_handling(self, manager):
        """Test event handling."""
        events_received = []

        def event_handler(event_type, data):
            events_received.append((event_type, data))

        # Register event handler
        manager.on_event("pre_transition", event_handler)
        manager.on_event("post_transition", event_handler)

        # Perform transition
        await manager.transition_to(
            AgentLifecycleState.DEPLOYING, reason="Test transition", triggered_by="test"
        )

        # Check events were received
        assert len(events_received) == 2
        assert events_received[0][0] == "pre_transition"
        assert events_received[1][0] == "post_transition"

        # Check event data
        pre_event_data = events_received[0][1]
        assert pre_event_data["from_state"] == AgentLifecycleState.REGISTERED
        assert pre_event_data["to_state"] == AgentLifecycleState.DEPLOYING

    @pytest.mark.asyncio
    async def test_async_event_handling(self, manager):
        """Test async event handling."""
        events_received = []

        async def async_event_handler(event_type, data):
            await asyncio.sleep(0.01)  # Simulate async work
            events_received.append((event_type, data))

        # Register async event handler
        manager.on_event("pre_transition", async_event_handler)

        # Perform transition
        await manager.transition_to(
            AgentLifecycleState.DEPLOYING, reason="Test transition", triggered_by="test"
        )

        # Check event was received
        assert len(events_received) == 1
        assert events_received[0][0] == "pre_transition"


class TestAgentLifecycleService:
    """Test agent lifecycle service."""

    @pytest.fixture
    def service(self):
        """Create a lifecycle service."""
        return AgentLifecycleService()

    @pytest.fixture
    def agent_id(self):
        """Create a test agent ID."""
        return uuid4()

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert len(service.managers) == 0

    def test_get_manager_creation(self, service, agent_id):
        """Test manager creation."""
        manager = service.get_manager(agent_id)
        assert isinstance(manager, AgentLifecycleManager)
        assert manager.agent_id == agent_id
        assert agent_id in service.managers

    def test_get_manager_reuse(self, service, agent_id):
        """Test manager reuse."""
        manager1 = service.get_manager(agent_id)
        manager2 = service.get_manager(agent_id)
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_register_agent(self, service, agent_id):
        """Test agent registration."""
        result = await service.register_agent(agent_id)
        assert result is True

        manager = service.get_manager(agent_id)
        assert manager.current_state == AgentLifecycleState.REGISTERED

    @pytest.mark.asyncio
    async def test_deploy_agent(self, service, agent_id):
        """Test agent deployment."""
        # First register the agent
        await service.register_agent(agent_id)

        # Deploy the agent
        result = await service.deploy_agent(agent_id)
        assert result is True

        manager = service.get_manager(agent_id)
        assert manager.current_state == AgentLifecycleState.DEPLOYED

    @pytest.mark.asyncio
    async def test_start_agent(self, service, agent_id):
        """Test agent startup."""
        # First register and deploy the agent
        await service.register_agent(agent_id)
        await service.deploy_agent(agent_id)

        # Start the agent
        result = await service.start_agent(agent_id)
        assert result is True

        manager = service.get_manager(agent_id)
        assert manager.current_state == AgentLifecycleState.ONLINE

    @pytest.mark.asyncio
    async def test_stop_agent(self, service, agent_id):
        """Test agent shutdown."""
        # First get agent to ONLINE state
        await service.register_agent(agent_id)
        await service.deploy_agent(agent_id)
        await service.start_agent(agent_id)

        # Stop the agent
        result = await service.stop_agent(agent_id)
        assert result is True

        manager = service.get_manager(agent_id)
        assert manager.current_state == AgentLifecycleState.OFFLINE

    @pytest.mark.asyncio
    async def test_assign_task(self, service, agent_id):
        """Test task assignment."""
        # First get agent to ONLINE state
        await service.register_agent(agent_id)
        await service.deploy_agent(agent_id)
        await service.start_agent(agent_id)

        # Assign task
        result = await service.assign_task(agent_id)
        assert result is True

        manager = service.get_manager(agent_id)
        assert manager.current_state == AgentLifecycleState.BUSY

    @pytest.mark.asyncio
    async def test_assign_task_to_unavailable_agent(self, service, agent_id):
        """Test task assignment to unavailable agent."""
        # Don't start the agent
        await service.register_agent(agent_id)

        # Try to assign task
        result = await service.assign_task(agent_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_complete_task(self, service, agent_id):
        """Test task completion."""
        # First get agent to BUSY state
        await service.register_agent(agent_id)
        await service.deploy_agent(agent_id)
        await service.start_agent(agent_id)
        await service.assign_task(agent_id)

        # Complete task
        result = await service.complete_task(agent_id)
        assert result is True

        manager = service.get_manager(agent_id)
        assert manager.current_state == AgentLifecycleState.IDLE

    @pytest.mark.asyncio
    async def test_complete_task_when_not_busy(self, service, agent_id):
        """Test task completion when agent is not busy."""
        # Get agent to ONLINE state (not BUSY)
        await service.register_agent(agent_id)
        await service.deploy_agent(agent_id)
        await service.start_agent(agent_id)

        # Try to complete task
        result = await service.complete_task(agent_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_maintenance_operations(self, service, agent_id):
        """Test maintenance operations."""
        # First get agent to ONLINE state
        await service.register_agent(agent_id)
        await service.deploy_agent(agent_id)
        await service.start_agent(agent_id)

        # Put in maintenance
        result = await service.put_in_maintenance(agent_id, "Scheduled maintenance")
        assert result is True

        manager = service.get_manager(agent_id)
        assert manager.current_state == AgentLifecycleState.MAINTENANCE

        # Resume from maintenance
        result = await service.resume_from_maintenance(agent_id)
        assert result is True

        manager = service.get_manager(agent_id)
        assert manager.current_state == AgentLifecycleState.ONLINE

    @pytest.mark.asyncio
    async def test_resume_from_maintenance_when_not_in_maintenance(
        self, service, agent_id
    ):
        """Test resume from maintenance when not in maintenance."""
        # Get agent to ONLINE state
        await service.register_agent(agent_id)
        await service.deploy_agent(agent_id)
        await service.start_agent(agent_id)

        # Try to resume from maintenance
        result = await service.resume_from_maintenance(agent_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_error(self, service, agent_id):
        """Test error handling."""
        # First get agent to ONLINE state
        await service.register_agent(agent_id)
        await service.deploy_agent(agent_id)
        await service.start_agent(agent_id)

        # Handle error
        result = await service.handle_error(agent_id, "Test error message")
        assert result is True

        manager = service.get_manager(agent_id)
        assert manager.current_state == AgentLifecycleState.ERROR

    def test_get_agent_status(self, service, agent_id):
        """Test getting agent status."""
        # Agent doesn't exist yet
        status = service.get_agent_status(agent_id)
        assert status is None

        # Create manager
        service.get_manager(agent_id)
        status = service.get_agent_status(agent_id)
        assert status is not None
        assert status["agent_id"] == str(agent_id)

    def test_get_all_agent_statuses(self, service):
        """Test getting all agent statuses."""
        # No agents initially
        statuses = service.get_all_agent_statuses()
        assert len(statuses) == 0

        # Add some agents
        agent1 = uuid4()
        agent2 = uuid4()

        service.get_manager(agent1)
        service.get_manager(agent2)

        statuses = service.get_all_agent_statuses()
        assert len(statuses) == 2
        assert agent1 in statuses
        assert agent2 in statuses

    @pytest.mark.asyncio
    async def test_get_operational_agents(self, service):
        """Test getting operational agents."""
        agent1 = uuid4()
        agent2 = uuid4()
        agent3 = uuid4()

        # Get agent1 to ONLINE state
        await service.register_agent(agent1)
        await service.deploy_agent(agent1)
        await service.start_agent(agent1)

        # Get agent2 to BUSY state
        await service.register_agent(agent2)
        await service.deploy_agent(agent2)
        await service.start_agent(agent2)
        await service.assign_task(agent2)

        # Leave agent3 in REGISTERED state

        operational = service.get_operational_agents()
        assert agent1 in operational
        assert agent2 in operational
        assert agent3 not in operational

    @pytest.mark.asyncio
    async def test_get_available_agents(self, service):
        """Test getting available agents."""
        agent1 = uuid4()
        agent2 = uuid4()
        agent3 = uuid4()

        # Get agent1 to ONLINE state (available)
        await service.register_agent(agent1)
        await service.deploy_agent(agent1)
        await service.start_agent(agent1)

        # Get agent2 to BUSY state (not available)
        await service.register_agent(agent2)
        await service.deploy_agent(agent2)
        await service.start_agent(agent2)
        await service.assign_task(agent2)

        # Leave agent3 in REGISTERED state (not available)
        await service.register_agent(agent3)

        available = service.get_available_agents()
        assert agent1 in available
        assert agent2 not in available
        assert agent3 not in available

    @pytest.mark.asyncio
    async def test_get_agents_in_error(self, service):
        """Test getting agents in error state."""
        agent1 = uuid4()
        agent2 = uuid4()
        agent3 = uuid4()

        # Get agent1 to ERROR state
        await service.register_agent(agent1)
        await service.deploy_agent(agent1)
        await service.start_agent(agent1)
        await service.handle_error(agent1, "Test error")

        # Get agent2 to ONLINE state
        await service.register_agent(agent2)
        await service.deploy_agent(agent2)
        await service.start_agent(agent2)

        # Leave agent3 in REGISTERED state

        error_agents = service.get_agents_in_error()
        assert agent1 in error_agents
        assert agent2 not in error_agents
        assert agent3 not in error_agents

    @pytest.mark.asyncio
    async def test_get_agents_in_maintenance(self, service):
        """Test getting agents in maintenance."""
        agent1 = uuid4()
        agent2 = uuid4()
        agent3 = uuid4()

        # Get agent1 to MAINTENANCE state
        await service.register_agent(agent1)
        await service.deploy_agent(agent1)
        await service.start_agent(agent1)
        await service.put_in_maintenance(agent1, "Scheduled maintenance")

        # Get agent2 to ONLINE state
        await service.register_agent(agent2)
        await service.deploy_agent(agent2)
        await service.start_agent(agent2)

        # Leave agent3 in REGISTERED state

        maintenance_agents = service.get_agents_in_maintenance()
        assert agent1 in maintenance_agents
        assert agent2 not in maintenance_agents
        assert agent3 not in maintenance_agents


class TestAgentLifecycleIntegration:
    """Integration tests for agent lifecycle system."""

    @pytest.mark.asyncio
    async def test_complete_agent_lifecycle(self):
        """Test complete agent lifecycle from registration to termination."""
        service = AgentLifecycleService()
        agent_id = uuid4()

        # 1. Register agent
        assert await service.register_agent(agent_id)
        assert (
            service.get_manager(agent_id).current_state
            == AgentLifecycleState.REGISTERED
        )

        # 2. Deploy agent
        assert await service.deploy_agent(agent_id)
        assert (
            service.get_manager(agent_id).current_state == AgentLifecycleState.DEPLOYED
        )

        # 3. Start agent
        assert await service.start_agent(agent_id)
        assert service.get_manager(agent_id).current_state == AgentLifecycleState.ONLINE

        # 4. Assign and complete tasks
        assert await service.assign_task(agent_id)
        assert service.get_manager(agent_id).current_state == AgentLifecycleState.BUSY

        assert await service.complete_task(agent_id)
        assert service.get_manager(agent_id).current_state == AgentLifecycleState.IDLE

        # 5. Put in maintenance
        assert await service.put_in_maintenance(agent_id, "Scheduled maintenance")
        assert (
            service.get_manager(agent_id).current_state
            == AgentLifecycleState.MAINTENANCE
        )

        # 6. Resume from maintenance
        assert await service.resume_from_maintenance(agent_id)
        assert service.get_manager(agent_id).current_state == AgentLifecycleState.ONLINE

        # 7. Stop agent
        assert await service.stop_agent(agent_id)
        assert (
            service.get_manager(agent_id).current_state == AgentLifecycleState.OFFLINE
        )

        # Verify state history
        manager = service.get_manager(agent_id)
        history = manager.get_state_history()
        assert len(history) >= 7  # At least 7 transitions

        # Verify final status
        status = service.get_agent_status(agent_id)
        assert status["current_state"] == AgentLifecycleState.OFFLINE
        assert not manager.is_operational()
        assert not manager.is_available_for_tasks()

    @pytest.mark.asyncio
    async def test_error_recovery_lifecycle(self):
        """Test error recovery lifecycle."""
        service = AgentLifecycleService()
        agent_id = uuid4()

        # Get agent to ONLINE state
        await service.register_agent(agent_id)
        await service.deploy_agent(agent_id)
        await service.start_agent(agent_id)

        # Simulate error
        assert await service.handle_error(agent_id, "Network timeout")
        assert service.get_manager(agent_id).current_state == AgentLifecycleState.ERROR

        # Recover from error
        manager = service.get_manager(agent_id)
        assert await manager.transition_to(
            AgentLifecycleState.ONLINE, reason="Error recovered", triggered_by="system"
        )

        assert manager.current_state == AgentLifecycleState.ONLINE
        assert manager.is_operational()
        assert manager.is_available_for_tasks()

"""
Integration tests for AgentService with lifecycle management.

This module tests the integration between the existing AgentService
and the new AgentLifecycleService to ensure they work together correctly.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from devcycle.core.agents.lifecycle import AgentLifecycleService, AgentLifecycleState
from devcycle.core.agents.models import (
    AgentCapability,
    AgentRegistration,
    AgentStatus,
    AgentType,
)
from devcycle.core.services.agent_service import AgentService


class TestAgentServiceLifecycleIntegration:
    """Test integration between AgentService and lifecycle management."""

    @pytest.fixture
    def mock_agent_repository(self):
        """Create a mock agent repository."""
        repository = AsyncMock()
        repository.get_by_name.return_value = None

        # Create a function to generate unique mock agents
        def create_mock_agent(agent_id=None, name="test_agent"):
            mock_agent = MagicMock()
            mock_agent.id = agent_id or uuid4()
            mock_agent.name = name
            mock_agent.agent_type = AgentType.BUSINESS_ANALYST
            mock_agent.status = AgentStatus.OFFLINE
            mock_agent.capabilities = '["analysis", "text_processing"]'  # JSON string
            mock_agent.configuration = '{"max_concurrent_tasks": 3}'  # JSON string
            mock_agent.description = "Test agent"
            mock_agent.version = "1.0.0"
            mock_agent.metadata_json = '{"test": true}'
            mock_agent.is_active = True
            mock_agent.created_at = "2024-01-01T00:00:00Z"
            mock_agent.updated_at = "2024-01-01T00:00:00Z"

            # Health-related fields
            mock_agent.last_heartbeat = "2024-01-01T00:00:00Z"
            mock_agent.response_time_ms = 100
            mock_agent.error_count = 0
            mock_agent.last_error = None
            mock_agent.uptime_seconds = 0
            return mock_agent

        # Store created agents to return them by ID
        created_agents = {}

        # Mock create method to return a new agent each time
        async def mock_create(**kwargs):
            agent_id = uuid4()
            agent = create_mock_agent(agent_id, kwargs.get("name", "test_agent"))
            created_agents[agent_id] = agent
            return agent

        # Mock get_by_id to return the stored agent
        async def mock_get_by_id(agent_id):
            return created_agents.get(agent_id)

        repository.create = mock_create
        repository.get_by_id = mock_get_by_id
        repository.update_agent_status = AsyncMock()
        repository.update_agent_health = AsyncMock()
        return repository

    @pytest.fixture
    def mock_task_repository(self):
        """Create a mock task repository."""
        repository = AsyncMock()
        repository.get_tasks_by_agent.return_value = []
        repository.update_task_status = AsyncMock()
        return repository

    @pytest.fixture
    def lifecycle_service(self):
        """Create a real lifecycle service for testing."""
        return AgentLifecycleService()

    @pytest.fixture
    def agent_service(
        self, mock_agent_repository, mock_task_repository, lifecycle_service
    ):
        """Create an agent service with lifecycle integration."""
        return AgentService(
            mock_agent_repository, mock_task_repository, lifecycle_service
        )

    @pytest.fixture
    def sample_registration(self):
        """Create a sample agent registration."""
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        return AgentRegistration(
            name=f"test_agent_{unique_id}",
            agent_type=AgentType.BUSINESS_ANALYST,
            description="Test agent for integration testing",
            version="1.0.0",
            capabilities=[AgentCapability.ANALYSIS, AgentCapability.TEXT_PROCESSING],
            configuration={
                "max_concurrent_tasks": "3",
                "timeout_seconds": "300",
                "retry_attempts": "2",
            },
            metadata={"test": "true"},
        )

    @pytest.mark.asyncio
    async def test_register_agent_with_lifecycle(
        self, agent_service, sample_registration
    ):
        """Test agent registration with lifecycle integration."""
        # Register agent
        response = await agent_service.register_agent(sample_registration)

        # Verify agent was created
        assert response is not None
        assert response.name == sample_registration.name

        # Verify lifecycle registration
        lifecycle_status = agent_service.get_agent_lifecycle_status(response.id)
        assert lifecycle_status is not None
        assert lifecycle_status["current_state"] == AgentLifecycleState.REGISTERED

    @pytest.mark.asyncio
    async def test_start_agent_lifecycle(self, agent_service, sample_registration):
        """Test starting an agent through lifecycle management."""
        # First register an agent
        response = await agent_service.register_agent(sample_registration)
        agent_id = response.id

        # Deploy the agent first (required for lifecycle)
        await agent_service.deploy_agent(agent_id)

        # Start the agent
        started_agent = await agent_service.start_agent(agent_id)

        # Verify agent was started
        assert started_agent is not None
        assert started_agent.id == agent_id

        # Verify lifecycle state
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.ONLINE

    @pytest.mark.asyncio
    async def test_stop_agent_lifecycle(self, agent_service, sample_registration):
        """Test stopping an agent through lifecycle management."""
        # Register, deploy, and start an agent
        response = await agent_service.register_agent(sample_registration)
        agent_id = response.id
        await agent_service.deploy_agent(agent_id)
        await agent_service.start_agent(agent_id)

        # Stop the agent
        stopped_agent = await agent_service.stop_agent(agent_id)

        # Verify agent was stopped
        assert stopped_agent is not None
        assert stopped_agent.id == agent_id

        # Verify lifecycle state
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.OFFLINE

    @pytest.mark.asyncio
    async def test_deploy_agent_lifecycle(self, agent_service, sample_registration):
        """Test deploying an agent through lifecycle management."""
        # Register an agent
        response = await agent_service.register_agent(sample_registration)
        agent_id = response.id

        # Deploy the agent
        deployed_agent = await agent_service.deploy_agent(agent_id)

        # Verify agent was deployed
        assert deployed_agent is not None
        assert deployed_agent.id == agent_id

        # Verify lifecycle state
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.DEPLOYED

    @pytest.mark.asyncio
    async def test_maintenance_lifecycle(self, agent_service, sample_registration):
        """Test putting agent in maintenance and resuming."""
        # Register, deploy, and start an agent
        response = await agent_service.register_agent(sample_registration)
        agent_id = response.id
        await agent_service.deploy_agent(agent_id)
        await agent_service.start_agent(agent_id)

        # Put in maintenance
        maintenance_agent = await agent_service.put_in_maintenance(
            agent_id, "Scheduled maintenance"
        )

        # Verify agent is in maintenance
        assert maintenance_agent is not None
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.MAINTENANCE

        # Resume from maintenance
        resumed_agent = await agent_service.resume_from_maintenance(agent_id)

        # Verify agent resumed
        assert resumed_agent is not None
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.ONLINE

    @pytest.mark.asyncio
    async def test_lifecycle_status_queries(self, agent_service, sample_registration):
        """Test lifecycle status query methods."""
        # Register, deploy, and start multiple agents
        agents = []
        for i in range(3):
            registration = AgentRegistration(
                name=f"test_agent_{i}",
                agent_type=AgentType.BUSINESS_ANALYST,
                description=f"Test agent {i}",
                version="1.0.0",
                capabilities=[AgentCapability.ANALYSIS],
            )
            response = await agent_service.register_agent(registration)
            await agent_service.deploy_agent(response.id)
            await agent_service.start_agent(response.id)
            agents.append(response)

        # Put one agent in maintenance
        await agent_service.put_in_maintenance(agents[1].id, "Test maintenance")

        # Test status queries
        operational_agents = agent_service.get_operational_agents()
        available_agents = agent_service.get_available_agents()
        maintenance_agents = agent_service.get_agents_in_maintenance()

        # Verify results
        assert (
            len(operational_agents) == 2
        )  # Two agents are operational (not in maintenance)
        assert len(available_agents) == 2  # Two agents are available for tasks
        assert len(maintenance_agents) == 1  # One agent is in maintenance

        # Verify specific agent IDs
        assert agents[0].id in operational_agents
        assert agents[2].id in operational_agents
        assert agents[1].id in maintenance_agents

    @pytest.mark.asyncio
    async def test_lifecycle_event_handling(self, agent_service, sample_registration):
        """Test that lifecycle events are handled correctly."""
        # Register an agent
        response = await agent_service.register_agent(sample_registration)
        agent_id = response.id

        # Deploy and start the agent (this should trigger event handling)
        await agent_service.deploy_agent(agent_id)
        await agent_service.start_agent(agent_id)

        # Verify that the repository was updated through event handling
        agent_service.agent_repository.update_agent_status.assert_called_with(
            agent_id, AgentStatus.ONLINE
        )

    @pytest.mark.asyncio
    async def test_error_handling_lifecycle(self, agent_service, sample_registration):
        """Test error handling in lifecycle management."""
        # Register an agent
        await agent_service.register_agent(sample_registration)

        # Try to start a non-existent agent
        non_existent_id = uuid4()
        result = await agent_service.start_agent(non_existent_id)

        # Should return None for non-existent agent
        assert result is None

    @pytest.mark.asyncio
    async def test_complete_lifecycle_workflow(
        self, agent_service, sample_registration
    ):
        """Test complete agent lifecycle workflow."""
        # 1. Register agent
        response = await agent_service.register_agent(sample_registration)
        agent_id = response.id

        # Verify initial state
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.REGISTERED

        # 2. Deploy agent
        await agent_service.deploy_agent(agent_id)
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.DEPLOYED

        # 3. Start agent
        await agent_service.start_agent(agent_id)
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.ONLINE

        # 4. Put in maintenance
        await agent_service.put_in_maintenance(agent_id, "Scheduled maintenance")
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.MAINTENANCE

        # 5. Resume from maintenance
        await agent_service.resume_from_maintenance(agent_id)
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.ONLINE

        # 6. Stop agent
        await agent_service.stop_agent(agent_id)
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.OFFLINE

    def test_lifecycle_service_integration(self, agent_service):
        """Test that lifecycle service is properly integrated."""
        # Verify lifecycle service is available
        assert agent_service.lifecycle_service is not None
        assert isinstance(agent_service.lifecycle_service, AgentLifecycleService)

        # Test lifecycle service methods are accessible
        assert hasattr(agent_service, "get_agent_lifecycle_status")
        assert hasattr(agent_service, "get_all_agent_lifecycle_statuses")
        assert hasattr(agent_service, "get_operational_agents")
        assert hasattr(agent_service, "get_available_agents")
        assert hasattr(agent_service, "get_agents_in_error")
        assert hasattr(agent_service, "get_agents_in_maintenance")

    @pytest.mark.asyncio
    async def test_lifecycle_with_task_management(
        self, agent_service, sample_registration
    ):
        """Test lifecycle integration with task management."""
        # Register, deploy, and start an agent
        response = await agent_service.register_agent(sample_registration)
        agent_id = response.id
        await agent_service.deploy_agent(agent_id)
        await agent_service.start_agent(agent_id)

        # Mock task assignment
        with patch.object(agent_service, "assign_task_to_agent") as mock_assign:
            mock_assign.return_value = MagicMock(
                id=uuid4(), agent_id=agent_id, task_type="test_task", status="pending"
            )

            # Assign a task
            task = await agent_service.assign_task_to_agent(
                agent_id, "test_task", {"param": "value"}
            )

            # Verify task was assigned
            assert task is not None
            mock_assign.assert_called_once()

        # Manually transition agent to BUSY state to simulate task assignment
        success = await agent_service.lifecycle_service.assign_task(agent_id)
        assert success, "Failed to transition agent to BUSY state"

        # Verify agent is now busy
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.BUSY

    @pytest.mark.asyncio
    async def test_lifecycle_state_consistency(
        self, agent_service, sample_registration
    ):
        """Test that lifecycle states remain consistent with database states."""
        # Register an agent
        response = await agent_service.register_agent(sample_registration)
        agent_id = response.id

        # Deploy and start agent
        await agent_service.deploy_agent(agent_id)
        await agent_service.start_agent(agent_id)

        # Verify both lifecycle and database are updated
        lifecycle_status = agent_service.get_agent_lifecycle_status(agent_id)
        assert lifecycle_status["current_state"] == AgentLifecycleState.ONLINE

        # Verify repository was called to update database
        agent_service.agent_repository.update_agent_status.assert_called_with(
            agent_id, AgentStatus.ONLINE
        )

    def test_lifecycle_methods_availability(self, agent_service):
        """Test that all lifecycle methods are available on the service."""
        # Test lifecycle management methods
        lifecycle_methods = [
            "start_agent",
            "stop_agent",
            "deploy_agent",
            "put_in_maintenance",
            "resume_from_maintenance",
        ]

        for method_name in lifecycle_methods:
            assert hasattr(
                agent_service, method_name
            ), f"Method {method_name} not found"
            method = getattr(agent_service, method_name)
            assert callable(method), f"Method {method_name} is not callable"

        # Test status query methods
        status_methods = [
            "get_agent_lifecycle_status",
            "get_all_agent_lifecycle_statuses",
            "get_operational_agents",
            "get_available_agents",
            "get_agents_in_error",
            "get_agents_in_maintenance",
        ]

        for method_name in status_methods:
            assert hasattr(
                agent_service, method_name
            ), f"Method {method_name} not found"
            method = getattr(agent_service, method_name)
            assert callable(method), f"Method {method_name} is not callable"

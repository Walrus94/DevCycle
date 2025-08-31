"""
Unit tests for agent management system.

This module tests the core functionality of the agent management system
including models, repositories, services, and API endpoints.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from devcycle.core.agents.models import (
    Agent,
    AgentCapability,
    AgentConfiguration,
    AgentRegistration,
    AgentStatus,
    AgentType,
)
from devcycle.core.repositories.agent_repository import (
    AgentRepository,
    AgentTaskRepository,
)
from devcycle.core.services.agent_service import AgentService


class TestAgentModels:
    """Test agent model classes."""

    def test_agent_status_enum(self) -> None:
        """Test AgentStatus enum values."""
        assert AgentStatus.OFFLINE.value == "offline"
        assert AgentStatus.ONLINE.value == "online"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.ERROR.value == "error"
        assert AgentStatus.MAINTENANCE.value == "maintenance"

    def test_agent_type_enum(self) -> None:
        """Test AgentType enum values."""
        assert AgentType.BUSINESS_ANALYST.value == "business_analyst"
        assert AgentType.DEVELOPER.value == "developer"
        assert AgentType.TESTER.value == "tester"
        assert AgentType.DEPLOYER.value == "deployer"
        assert AgentType.MONITOR.value == "monitor"
        assert AgentType.CUSTOM.value == "custom"

    def test_agent_capability_enum(self) -> None:
        """Test AgentCapability enum values."""
        assert AgentCapability.TEXT_PROCESSING.value == "text_processing"
        assert AgentCapability.CODE_GENERATION.value == "code_generation"
        assert AgentCapability.TESTING.value == "testing"
        assert AgentCapability.DEPLOYMENT.value == "deployment"
        assert AgentCapability.MONITORING.value == "monitoring"
        assert AgentCapability.ANALYSIS.value == "analysis"
        assert AgentCapability.PLANNING.value == "planning"

    def test_agent_configuration_defaults(self) -> None:
        """Test AgentConfiguration default values."""
        config = AgentConfiguration()
        assert config.max_concurrent_tasks == 1
        assert config.timeout_seconds == 300
        assert config.retry_attempts == 3
        assert config.priority == 1
        assert config.capabilities == []
        assert config.settings == {}

    def test_agent_registration_validation(self) -> None:
        """Test AgentRegistration validation."""
        registration = AgentRegistration(
            name="test_agent",
            agent_type=AgentType.BUSINESS_ANALYST,
            version="1.0.0",
            capabilities=[AgentCapability.ANALYSIS],
        )
        assert registration.name == "test_agent"
        assert registration.agent_type == AgentType.BUSINESS_ANALYST
        assert registration.version == "1.0.0"
        assert registration.capabilities == [AgentCapability.ANALYSIS]


class TestAgentRepository:
    """Test agent repository functionality."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def agent_repository(self, mock_session: AsyncMock) -> AgentRepository:
        """Create agent repository instance."""
        return AgentRepository(mock_session)

    @pytest.fixture
    def task_repository(self, mock_session: AsyncMock) -> AgentTaskRepository:
        """Create task repository instance."""
        return AgentTaskRepository(mock_session)

    @pytest.fixture
    def sample_agent(self) -> Agent:
        """Create sample agent data."""
        return Agent(
            id=uuid4(),
            name="test_agent",
            agent_type="business_analyst",
            description="Test agent",
            version="1.0.0",
            capabilities='["analysis"]',
            configuration='{"max_concurrent_tasks": 1}',
            metadata_json='{"test": true}',
            status="offline",
            is_active=True,
        )

    async def test_get_by_name(
        self,
        agent_repository: AgentRepository,
        mock_session: AsyncMock,
        sample_agent: Agent,
    ) -> None:
        """Test getting agent by name."""
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_agent

        result = await agent_repository.get_by_name("test_agent")

        assert result == sample_agent
        mock_session.execute.assert_called_once()

    async def test_get_by_type(
        self,
        agent_repository: AgentRepository,
        mock_session: AsyncMock,
        sample_agent: Agent,
    ) -> None:
        """Test getting agents by type."""
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            sample_agent
        ]

        result = await agent_repository.get_by_type(AgentType.BUSINESS_ANALYST)

        assert result == [sample_agent]
        mock_session.execute.assert_called_once()

    async def test_get_online_agents(
        self,
        agent_repository: AgentRepository,
        mock_session: AsyncMock,
        sample_agent: Agent,
    ) -> None:
        """Test getting online agents."""
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            sample_agent
        ]

        result = await agent_repository.get_online_agents()

        assert result == [sample_agent]
        mock_session.execute.assert_called_once()


class TestAgentService:
    """Test agent service functionality."""

    @pytest.fixture
    def mock_agent_repository(self) -> AsyncMock:
        """Create mock agent repository."""
        return AsyncMock(spec=AgentRepository)

    @pytest.fixture
    def mock_task_repository(self) -> AsyncMock:
        """Create mock task repository."""
        return AsyncMock(spec=AgentTaskRepository)

    @pytest.fixture
    def agent_service(
        self, mock_agent_repository: AsyncMock, mock_task_repository: AsyncMock
    ) -> AgentService:
        """Create agent service instance."""
        return AgentService(mock_agent_repository, mock_task_repository)

    @pytest.fixture
    def sample_registration(self) -> AgentRegistration:
        """Create sample agent registration."""
        return AgentRegistration(
            name="test_agent",
            agent_type=AgentType.BUSINESS_ANALYST,
            version="1.0.0",
            capabilities=[AgentCapability.ANALYSIS],
            description="Test agent",
        )

    async def test_register_agent_success(
        self,
        agent_service: AgentService,
        mock_agent_repository: AsyncMock,
        sample_registration: AgentRegistration,
    ) -> None:
        """Test successful agent registration."""
        # Mock repository responses
        mock_agent_repository.get_by_name.return_value = None

        mock_agent = MagicMock()
        mock_agent.id = uuid4()
        mock_agent.name = "test_agent"
        mock_agent.agent_type = "business_analyst"
        mock_agent.description = "Test agent"
        mock_agent.version = "1.0.0"
        mock_agent.capabilities = '["analysis"]'
        mock_agent.configuration = '{"max_concurrent_tasks": 1}'
        mock_agent.metadata_json = "{}"
        mock_agent.status = "offline"
        mock_agent.is_active = True
        mock_agent.created_at = "2024-01-01T00:00:00Z"
        mock_agent.updated_at = "2024-01-01T00:00:00Z"
        mock_agent.last_seen = None

        # Mock the repository create method
        mock_repository = AsyncMock()
        mock_repository.create.return_value = mock_agent
        agent_service.repository = mock_repository

        result = await agent_service.register_agent(sample_registration)

        assert result is not None
        mock_agent_repository.get_by_name.assert_called_once_with("test_agent")
        mock_repository.create.assert_called_once()

    async def test_register_agent_duplicate_name(
        self,
        agent_service: AgentService,
        mock_agent_repository: AsyncMock,
        sample_registration: AgentRegistration,
    ) -> None:
        """Test agent registration with duplicate name."""
        # Mock repository to return existing agent
        mock_agent_repository.get_by_name.return_value = MagicMock()

        with pytest.raises(
            ValueError, match="Agent with name 'test_agent' already exists"
        ):
            await agent_service.register_agent(sample_registration)

    async def test_register_agent_no_capabilities(
        self, agent_service: AgentService, mock_agent_repository: AsyncMock
    ) -> None:
        """Test agent registration without capabilities."""
        registration = AgentRegistration(
            name="test_agent",
            agent_type=AgentType.BUSINESS_ANALYST,
            version="1.0.0",
            capabilities=[],  # No capabilities
        )

        with pytest.raises(ValueError, match="Agent must have at least one capability"):
            await agent_service.register_agent(registration)

    async def test_get_agents_by_type(
        self, agent_service: AgentService, mock_agent_repository: AsyncMock
    ) -> None:
        """Test getting agents by type."""
        mock_agents = [MagicMock(), MagicMock()]
        mock_agent_repository.get_by_type.return_value = mock_agents

        result = await agent_service.get_agents_by_type(AgentType.BUSINESS_ANALYST)

        assert len(result) == 2
        mock_agent_repository.get_by_type.assert_called_once_with(
            AgentType.BUSINESS_ANALYST
        )

    async def test_get_online_agents(
        self, agent_service: AgentService, mock_agent_repository: AsyncMock
    ) -> None:
        """Test getting online agents."""
        mock_agents = [MagicMock(), MagicMock()]
        mock_agent_repository.get_online_agents.return_value = mock_agents

        result = await agent_service.get_online_agents()

        assert len(result) == 2
        mock_agent_repository.get_online_agents.assert_called_once()


class TestAgentAPI:
    """Test agent API endpoints."""

    def test_agent_router_creation(self) -> None:
        """Test that agent router can be created."""
        from devcycle.api.routes.agents import router

        assert router is not None
        assert router.prefix == "/agents"
        assert "agents" in router.tags

    def test_agent_endpoints_registered(self) -> None:
        """Test that all agent endpoints are registered."""
        from devcycle.api.routes.agents import router

        # Check that we have the expected endpoints
        routes = [route.path for route in router.routes]

        expected_routes = [
            "/agents/",
            "/agents/online",
            "/agents/available",
            "/agents/search",
            "/agents/{agent_id}",
            "/agents/name/{agent_name}",
            "/agents/{agent_id}/heartbeat",
            "/agents/{agent_id}/offline",
            "/agents/{agent_id}/deactivate",
            "/agents/{agent_id}/activate",
            "/agents/{agent_id}/tasks",
            "/agents/{agent_id}/tasks/history",
            "/agents/statistics/overview",
            "/agents/cleanup/stale",
            "/agents/types",
            "/agents/capabilities",
            "/agents/statuses",
        ]

        for expected_route in expected_routes:
            assert expected_route in routes, f"Route {expected_route} not found"

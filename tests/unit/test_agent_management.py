"""
Unit tests for agent management system.

This module tests the core functionality of the agent management system
including models, repositories, services, and API endpoints.
"""

from datetime import datetime, timezone
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
            description="Test agent for unit testing",
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

    @pytest.mark.asyncio
    async def test_get_by_name(
        self,
        agent_repository: AgentRepository,
        mock_session: AsyncMock,
        sample_agent: Agent,
    ) -> None:
        """Test getting agent by name."""
        # Create a proper mock result object
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_agent
        # Mock execute as an async method that returns the result
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await agent_repository.get_by_name("test_agent")

        assert result == sample_agent
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_type(
        self,
        agent_repository: AgentRepository,
        mock_session: AsyncMock,
        sample_agent: Agent,
    ) -> None:
        """Test getting agents by type."""
        # Create a proper mock result object
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_agent]
        mock_result.scalars.return_value = mock_scalars
        # Mock execute as an async method that returns the result
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await agent_repository.get_by_type(AgentType.BUSINESS_ANALYST)

        assert result == [sample_agent]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_online_agents(
        self,
        agent_repository: AgentRepository,
        mock_session: AsyncMock,
        sample_agent: Agent,
    ) -> None:
        """Test getting online agents."""
        # Create a proper mock result object
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_agent]
        mock_result.scalars.return_value = mock_scalars
        # Mock execute as an async method that returns the result
        mock_session.execute = AsyncMock(return_value=mock_result)

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

    @pytest.mark.asyncio
    async def test_register_agent_success(
        self,
        agent_service: AgentService,
        mock_agent_repository: AsyncMock,
        sample_registration: AgentRegistration,
    ) -> None:
        """Test successful agent registration."""
        # Mock repository responses
        mock_agent_repository.get_by_name.return_value = None

        # Create a proper Agent object instead of MagicMock
        mock_agent = Agent(
            id=uuid4(),
            name="test_agent",
            agent_type="business_analyst",
            description="Test agent",
            version="1.0.0",
            capabilities='["analysis"]',
            configuration='{"max_concurrent_tasks": 1}',
            metadata_json="{}",
            status="offline",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_seen=None,
            last_heartbeat=None,
            response_time_ms=None,
            error_count=0,
            last_error=None,
            uptime_seconds=0,
        )

        # Mock the repository create method
        mock_agent_repository.create.return_value = mock_agent

        result = await agent_service.register_agent(sample_registration)

        assert result is not None
        mock_agent_repository.get_by_name.assert_called_once_with("test_agent")
        mock_agent_repository.create.assert_called_once()

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_register_agent_no_capabilities(
        self, agent_service: AgentService, mock_agent_repository: AsyncMock
    ) -> None:
        """Test agent registration without capabilities."""
        # Mock the repository to return None (no existing agent)
        mock_agent_repository.get_by_name.return_value = None

        registration = AgentRegistration(
            name="test_agent",
            agent_type=AgentType.BUSINESS_ANALYST,
            description="Test agent for validation",
            version="1.0.0",
            capabilities=[],  # No capabilities
        )

        with pytest.raises(ValueError, match="Agent must have at least one capability"):
            await agent_service.register_agent(registration)

    @pytest.mark.asyncio
    async def test_get_agents_by_type(
        self, agent_service: AgentService, mock_agent_repository: AsyncMock
    ) -> None:
        """Test getting agents by type."""
        # Create proper Agent objects instead of MagicMock
        mock_agents = [
            Agent(
                id=uuid4(),
                name="agent1",
                agent_type="business_analyst",
                description="Test agent 1",
                version="1.0.0",
                capabilities='["analysis"]',
                configuration='{"max_concurrent_tasks": 1}',
                metadata_json="{}",
                status="online",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_seen=None,
                last_heartbeat=None,
                response_time_ms=None,
                error_count=0,
                last_error=None,
                uptime_seconds=0,
            ),
            Agent(
                id=uuid4(),
                name="agent2",
                agent_type="business_analyst",
                description="Test agent 2",
                version="1.0.0",
                capabilities='["analysis"]',
                configuration='{"max_concurrent_tasks": 1}',
                metadata_json="{}",
                status="online",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_seen=None,
                last_heartbeat=None,
                response_time_ms=None,
                error_count=0,
                last_error=None,
                uptime_seconds=0,
            ),
        ]
        mock_agent_repository.get_by_type.return_value = mock_agents

        result = await agent_service.get_agents_by_type(AgentType.BUSINESS_ANALYST)

        assert len(result) == 2
        mock_agent_repository.get_by_type.assert_called_once_with(
            AgentType.BUSINESS_ANALYST
        )

    @pytest.mark.asyncio
    async def test_get_online_agents(
        self, agent_service: AgentService, mock_agent_repository: AsyncMock
    ) -> None:
        """Test getting online agents."""
        # Create proper Agent objects instead of MagicMock
        mock_agents = [
            Agent(
                id=uuid4(),
                name="agent1",
                agent_type="business_analyst",
                description="Test agent 1",
                version="1.0.0",
                capabilities='["analysis"]',
                configuration='{"max_concurrent_tasks": 1}',
                metadata_json="{}",
                status="online",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_seen=None,
                last_heartbeat=None,
                response_time_ms=None,
                error_count=0,
                last_error=None,
                uptime_seconds=0,
            ),
            Agent(
                id=uuid4(),
                name="agent2",
                agent_type="business_analyst",
                description="Test agent 2",
                version="1.0.0",
                capabilities='["analysis"]',
                configuration='{"max_concurrent_tasks": 1}',
                metadata_json="{}",
                status="online",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_seen=None,
                last_heartbeat=None,
                response_time_ms=None,
                error_count=0,
                last_error=None,
                uptime_seconds=0,
            ),
        ]
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

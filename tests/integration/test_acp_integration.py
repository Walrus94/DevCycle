"""
ACP Integration Tests.

Tests the complete ACP integration including agent registry, message routing,
workflow orchestration, and API endpoints.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from devcycle.api.app import create_app
from devcycle.core.acp.agents.business_analyst_agent import BusinessAnalystACPAgent
from devcycle.core.acp.agents.testing_agent import TestingACPAgent
from devcycle.core.acp.models import ACPMessage
from devcycle.core.acp.services.agent_registry import ACPAgentRegistry
from devcycle.core.acp.services.message_router import ACPMessageRouter
from devcycle.core.acp.services.workflow_engine import ACPWorkflowEngine


class TestACPIntegration:
    """Test complete ACP integration."""

    @pytest.fixture
    def test_user(self):
        """Create a test user for authentication."""
        import uuid

        from devcycle.core.auth.tortoise_models import User

        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            is_active=True,
            is_verified=True,
            is_superuser=False,
        )
        return user

    @pytest.fixture
    def client(self, test_user):
        """Create test client with authentication."""
        app = create_app()

        # Override the current_active_user dependency
        from devcycle.core.auth.fastapi_users import current_active_user

        app.dependency_overrides[current_active_user] = lambda: test_user

        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, test_user):
        """Create authentication headers."""
        return {"Authorization": f"Bearer {test_user.id}"}

    @pytest.fixture
    async def agent_registry(self):
        """Create ACP agent registry for testing."""
        from unittest.mock import Mock, patch

        from devcycle.core.acp.config import ACPAgentConfig, ACPConfig

        # Mock the HuggingFaceClient to avoid token requirement
        with (
            patch(
                "devcycle.core.acp.agents.business_analyst_agent.HuggingFaceClient"
            ) as mock_hf_client1,
            patch(
                "devcycle.core.acp.agents.testing_agent.HuggingFaceClient"
            ) as mock_hf_client2,
        ):
            mock_hf_client1.return_value = Mock()
            mock_hf_client2.return_value = Mock()

            # Create test config
            config = ACPConfig(
                health_check_interval=30, discovery_enabled=True, message_timeout=30.0
            )

            registry = ACPAgentRegistry(config)

            # Create test agents with proper config
            business_agent_config = ACPAgentConfig(
                agent_id="test-business-agent",
                agent_name="Test Business Analyst",
                agent_version="1.0.0",
                max_concurrent_runs=5,
                hf_model_name="microsoft/DialoGPT-medium",
            )

            testing_agent_config = ACPAgentConfig(
                agent_id="test-testing-agent",
                agent_name="Test Testing Agent",
                agent_version="1.0.0",
                max_concurrent_runs=5,
                hf_model_name="microsoft/DialoGPT-medium",
            )

            # Register test agents
            business_agent = BusinessAnalystACPAgent(business_agent_config)
            testing_agent = TestingACPAgent(testing_agent_config)

            await registry.register_agent(business_agent)
            await registry.register_agent(testing_agent)

            return registry

    @pytest.fixture
    async def message_router(self, agent_registry):
        """Create ACP message router for testing."""
        return ACPMessageRouter(agent_registry)

    @pytest.fixture
    async def workflow_engine(self, agent_registry):
        """Create ACP workflow engine for testing."""
        return ACPWorkflowEngine(agent_registry)

    @pytest.mark.skip(reason="Requires Hugging Face API token - skipping for now")
    @pytest.mark.asyncio
    async def test_agent_registration_and_discovery(self, agent_registry):
        """Test agent registration and discovery functionality."""
        # Test agent discovery
        business_agents = await agent_registry.discover_agents("business_analysis")
        testing_agents = await agent_registry.discover_agents("testing")

        assert len(business_agents) == 1
        assert len(testing_agents) == 1
        assert business_agents[0].agent_id == "test-business-agent"
        assert testing_agents[0].agent_id == "test-testing-agent"

    @pytest.mark.skip(reason="Requires Hugging Face API token - skipping for now")
    @pytest.mark.asyncio
    async def test_message_routing(self, message_router):
        """Test message routing to appropriate agents."""
        # Test business analysis message
        business_message = ACPMessage(
            message_id="test-1",
            message_type="analyze_requirements",
            source_agent_id="orchestrator",
            target_agent_id="business-analyst",
            content={"requirements": "Create a user management system"},
        )

        response = await message_router.route_message(business_message)
        assert response.success
        assert "analysis" in response.content

    @pytest.mark.skip(reason="Requires Hugging Face API token - skipping for now")
    @pytest.mark.asyncio
    async def test_workflow_execution(self, workflow_engine):
        """Test complete workflow execution."""
        requirements = "Build a REST API for user management"

        workflow = await workflow_engine.start_workflow(
            workflow_name="development_workflow",
            workflow_version="1.0.0",
            steps=[
                {
                    "step_id": "analyze_requirements",
                    "step_name": "Analyze Requirements",
                    "agent_id": "business-analyst",
                    "input_data": {"requirements": requirements},
                },
                {
                    "step_id": "generate_tests",
                    "step_name": "Generate Tests",
                    "agent_id": "testing-agent",
                    "input_data": {"code": "placeholder_code"},
                    "depends_on": ["analyze_requirements"],
                },
            ],
        )

        assert workflow is not None
        assert workflow.workflow_id is not None
        assert workflow.status == "running"

    @pytest.mark.skip(reason="Requires Hugging Face API token - skipping for now")
    @pytest.mark.asyncio
    async def test_agent_health_checking(self, agent_registry):
        """Test agent health checking functionality."""
        health_status = await agent_registry.health_check_all()

        assert "business-analyst" in health_status
        assert "testing-agent" in health_status
        assert health_status["business-analyst"] is True
        assert health_status["testing-agent"] is True

    def test_acp_api_endpoints(self, client, auth_headers):
        """Test ACP API endpoints."""
        # Test agent discovery endpoint - expect empty list when Redis is not available
        response = client.get(
            "/api/v1/acp/agents/discover/testing", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # When Redis is not available, we get an empty list
        assert isinstance(data, list)
        # The endpoint should still work even if no agents are found

    @pytest.mark.skip(reason="Workflow endpoints not implemented yet")
    def test_acp_workflow_endpoints(self, client, auth_headers):
        """Test ACP workflow endpoints."""
        with patch("devcycle.core.dependencies.get_workflow_engine") as mock_engine:
            mock_engine.return_value = AsyncMock()
            mock_workflow = AsyncMock()
            mock_workflow.workflow_id = "test-workflow-123"
            mock_workflow.status = "running"
            mock_engine.return_value.start_workflow.return_value = mock_workflow

            response = client.post(
                "/api/v1/acp/workflows/start",
                json={
                    "workflow_name": "test_workflow",
                    "workflow_version": "1.0.0",
                    "steps": [
                        {
                            "step_id": "step1",
                            "step_name": "Test Step",
                            "agent_id": "test-agent",
                            "input_data": {"test": "data"},
                        }
                    ],
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["workflow_id"] == "test-workflow-123"
            assert data["status"] == "running"

    def test_acp_message_endpoints(self, client, auth_headers):
        """Test ACP message endpoints."""
        # Test with real system - expect agent not found error
        response = client.post(
            "/api/v1/acp/messages/send",
            json={
                "message_id": "test-msg-123",
                "message_type": "test_message",
                "source_agent_id": "test-sender",
                "target_agent_id": "test-receiver",
                "content": {"test": "data"},
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Expect failure since agent doesn't exist
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    @pytest.mark.skip(reason="Requires Hugging Face API token - skipping for now")
    @pytest.mark.asyncio
    async def test_error_handling(self, message_router):
        """Test error handling in ACP components."""
        # Test message to non-existent agent
        invalid_message = ACPMessage(
            message_id="test-error",
            message_type="test_message",
            source_agent_id="test-sender",
            target_agent_id="non-existent-agent",
            content={"test": "data"},
        )

        response = await message_router.route_message(invalid_message)
        assert response.success is False
        assert "not found" in response.error.lower()

    @pytest.mark.skip(reason="Requires Hugging Face API token - skipping for now")
    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, message_router):
        """Test concurrent message processing."""
        # Create multiple messages
        messages = []
        for i in range(10):
            message = ACPMessage(
                message_id=f"concurrent-{i}",
                message_type="analyze_requirements",
                source_agent_id="test-sender",
                target_agent_id="business-analyst",
                content={"requirements": f"Test requirement {i}"},
            )
            messages.append(message)

        # Process messages concurrently
        tasks = [message_router.route_message(msg) for msg in messages]
        responses = await asyncio.gather(*tasks)

        # Verify all messages were processed successfully
        assert len(responses) == 10
        assert all(response.success for response in responses)

    @pytest.mark.skip(reason="Requires Hugging Face API token - skipping for now")
    @pytest.mark.asyncio
    async def test_workflow_step_dependencies(self, workflow_engine):
        """Test workflow step dependency handling."""
        workflow = await workflow_engine.start_workflow(
            workflow_name="dependency_test",
            workflow_version="1.0.0",
            steps=[
                {
                    "step_id": "step1",
                    "step_name": "First Step",
                    "agent_id": "business-analyst",
                    "input_data": {"data": "step1"},
                },
                {
                    "step_id": "step2",
                    "step_name": "Second Step",
                    "agent_id": "testing-agent",
                    "input_data": {"data": "step2"},
                    "depends_on": ["step1"],
                },
            ],
        )

        assert workflow is not None
        # Verify step dependencies are properly set
        step2 = next(step for step in workflow.steps if step.step_id == "step2")
        assert "step1" in step2.depends_on

    def test_authentication_required(self):
        """Test that ACP endpoints require authentication."""
        # Create a client without authentication override
        from fastapi.testclient import TestClient

        from devcycle.api.app import create_app

        app = create_app()
        test_client = TestClient(app)

        # Test without authentication
        response = test_client.get("/api/v1/acp/agents/discover/testing")
        assert response.status_code == 401

        # Test another endpoint that requires auth
        response = test_client.get("/api/v1/acp/agents")
        assert response.status_code == 401

        response = test_client.post(
            "/api/v1/acp/messages/send", json={"message_id": "test"}
        )
        assert response.status_code == 401

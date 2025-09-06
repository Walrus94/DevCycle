"""
Tests for ACP API endpoints.

These tests verify the ACP API integration with FastAPI.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from devcycle.api.app import create_app
from devcycle.core.auth.tortoise_models import User


class TestACPApi:
    """Test ACP API endpoints."""

    @pytest.fixture
    def client(self, test_user):
        """Create test client."""
        app = create_app()

        # Override the current_active_user dependency
        from devcycle.core.auth.fastapi_users import current_active_user

        app.dependency_overrides[current_active_user] = lambda: test_user

        return TestClient(app)

    @pytest.fixture
    def test_user(self):
        """Create a test user."""
        from uuid import uuid4

        return User(
            id=uuid4(), email="test@example.com", is_active=True, is_verified=True
        )

    @pytest.fixture
    def auth_headers(self, test_user):
        """Create authentication headers."""
        # In a real test, you'd get a proper JWT token
        # For now, we'll mock the authentication
        return {"Authorization": "Bearer test-token"}

    def test_acp_health_endpoint(self, client, test_user, auth_headers):
        """Test ACP health endpoint."""
        with patch("devcycle.api.routes.acp.get_agent_registry") as mock_registry:
            mock_registry.return_value = AsyncMock()
            mock_registry.return_value.health_check_all.return_value = {
                "test-agent": True
            }
            mock_registry.return_value.get_metrics.return_value = {"total_agents": 1}

            response = client.get("/api/v1/acp/health", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "agent_health" in data
            assert "metrics" in data

    def test_acp_agents_list_endpoint(self, client, test_user, auth_headers):
        """Test ACP agents list endpoint."""
        with patch("devcycle.api.routes.acp.get_agent_registry") as mock_registry:
            mock_registry.return_value = AsyncMock()
            mock_registry.return_value.list_agents.return_value = []

            response = client.get("/api/v1/acp/agents", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_acp_agent_registration(self, client, test_user, auth_headers):
        """Test ACP agent registration."""
        with patch("devcycle.api.routes.acp.get_agent_registry") as mock_registry:
            mock_registry.return_value = AsyncMock()
            mock_registry.return_value.register_agent.return_value = True

            agent_data = {
                "agent_id": "test-agent",
                "agent_name": "Test Agent",
                "capabilities": ["testing"],
                "input_types": ["test_request"],
                "output_types": ["test_result"],
            }

            response = client.post(
                "/api/v1/acp/agents/register", json=agent_data, headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Agent registered successfully"
            assert data["agent_id"] == "test-agent"

    def test_acp_message_sending(self, client, test_user, auth_headers):
        """Test ACP message sending."""
        # This is an integration test, so we test the real system behavior
        # The system should return an error because no agent is registered
        message_data = {
            "message_type": "request",
            "content": {"test": "data"},
            "target_agent_id": "test-agent",
        }

        response = client.post(
            "/api/v1/acp/messages/send", json=message_data, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # In integration test, we expect the system to work but return an error
        # because no agent is registered (which is expected behavior)
        assert data["success"] is False
        assert "error" in data
        assert data["error"] == "Target agent test-agent not found"

    def test_acp_quick_code_generation(self, client, test_user, auth_headers):
        """Test ACP quick code generation."""
        from devcycle.core.acp.models import ACPResponse

        ACPResponse(
            response_id="resp_quick-code-1",
            message_id="quick-code-1",
            success=True,
            content={"generated_code": "def hello(): pass"},
        )

        # This is an integration test, so we test the real system behavior
        # The system should return an error because no agent is registered
        response = client.post(
            "/api/v1/acp/quick/generate-code",
            params={
                "requirements": "Create a hello world function",
                "language": "python",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        print(f"DEBUG: Response data: {data}")

        # In integration test, we expect the system to work but return an error
        # because no agent is registered (which is expected behavior)
        assert data["success"] is False
        assert "error" in data
        assert data["error"] == "Target agent code-generator not found"

    def test_acp_quick_test_generation(self, client, test_user, auth_headers):
        """Test ACP quick test generation."""
        # This is an integration test, so we test the real system behavior
        # The system should return an error because no agent is registered
        response = client.post(
            "/api/v1/acp/quick/generate-tests",
            params={
                "code": "def hello(): pass",
                "language": "python",
                "test_framework": "pytest",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # In integration test, we expect the system to work but return an error
        # because no agent is registered (which is expected behavior)
        assert data["success"] is False
        assert "error" in data
        assert data["error"] == "Target agent testing not found"

    def test_acp_quick_requirements_analysis(self, client, test_user, auth_headers):
        """Test ACP quick requirements analysis."""
        # This is an integration test, so we test the real system behavior
        # The system should return an error because no agent is registered
        response = client.post(
            "/api/v1/acp/quick/analyze-requirements",
            params={
                "project_description": "Test project",
                "business_context": "Test context",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # In integration test, we expect the system to work but return an error
        # because no agent is registered (which is expected behavior)
        assert data["success"] is False
        assert "error" in data
        assert data["error"] == "Target agent business-analyst not found"

    def test_acp_agent_discovery(self, client, test_user, auth_headers):
        """Test ACP agent discovery by capability."""
        with patch("devcycle.api.routes.acp.get_agent_registry") as mock_registry:
            mock_registry.return_value = AsyncMock()
            mock_registry.return_value.discover_agents.return_value = []

            response = client.get(
                "/api/v1/acp/agents/discover/code_generation", headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_acp_metrics_endpoint(self, client, test_user, auth_headers):
        """Test ACP metrics endpoint."""
        with (
            patch("devcycle.api.routes.acp.get_agent_registry") as mock_registry,
            patch("devcycle.api.routes.acp.get_message_router") as mock_router,
        ):

            mock_registry.return_value = AsyncMock()
            mock_registry.return_value.get_metrics.return_value = {"total_agents": 1}
            mock_router.return_value = AsyncMock()
            mock_router.return_value.get_stats.return_value = {"messages_processed": 10}

            response = client.get("/api/v1/acp/metrics", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "registry" in data
            assert "router" in data
            assert "timestamp" in data


if __name__ == "__main__":
    pytest.main([__file__])

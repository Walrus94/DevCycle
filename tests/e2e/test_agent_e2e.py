"""
End-to-end tests for agent management system.

These tests require Docker services to be running.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.asyncio
class TestAgentE2E:
    """End-to-end tests for agent management."""

    @pytest.mark.asyncio
    async def test_agent_registration_workflow(self, authenticated_client: AsyncClient):
        """Test complete agent registration workflow."""
        # Test agent registration
        registration_data = {
            "name": "test_e2e_agent",
            "agent_type": "business_analyst",
            "version": "1.0.0",
            "capabilities": ["analysis"],
            "description": "Test agent for e2e testing",
        }

        response = await authenticated_client.post(
            "/api/v1/agents/", json=registration_data
        )
        assert response.status_code == 201  # Changed from 200 to 201 (Created)

        agent_data = response.json()
        assert agent_data["name"] == "test_e2e_agent"
        assert agent_data["agent_type"] == "business_analyst"
        assert agent_data["status"] == "offline"

        agent_id = agent_data["id"]

        # Test getting agent by ID
        response = await authenticated_client.get(f"/api/v1/agents/{agent_id}")
        assert response.status_code == 200

        # Test agent heartbeat
        heartbeat_data = {
            "agent_id": agent_id,
            "status": "online",
            "current_task": None,
            "resource_usage": {"cpu": 50, "memory": 1024},
            "error_message": None,
        }

        response = await authenticated_client.post(
            f"/api/v1/agents/{agent_id}/heartbeat", json=heartbeat_data
        )
        assert response.status_code == 200

        # Test getting online agents
        response = await authenticated_client.get("/api/v1/agents/online")
        assert response.status_code == 200
        online_agents = response.json()
        assert len(online_agents) >= 1

        # Test agent search
        response = await authenticated_client.get(
            "/api/v1/agents/search?query=test_e2e_agent"
        )
        assert response.status_code == 200
        search_results = response.json()
        assert len(search_results) >= 1
        assert any(agent["name"] == "test_e2e_agent" for agent in search_results)

        # Test agent deactivation
        response = await authenticated_client.post(
            f"/api/v1/agents/{agent_id}/deactivate"
        )
        assert response.status_code == 200

        # Test agent deletion
        response = await authenticated_client.delete(f"/api/v1/agents/{agent_id}")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_agent_types_and_capabilities(self, async_client: AsyncClient):
        """Test agent types and capabilities endpoints."""
        # Test getting agent types
        response = await async_client.get("/api/v1/agents/types")
        assert response.status_code == 200
        types = response.json()
        assert "business_analyst" in types
        assert "developer" in types

        # Test getting agent capabilities
        response = await async_client.get("/api/v1/agents/capabilities")
        assert response.status_code == 200
        capabilities = response.json()
        assert "analysis" in capabilities
        assert "code_generation" in capabilities

    @pytest.mark.asyncio
    async def test_agent_statistics(self, async_client: AsyncClient):
        """Test agent statistics endpoint."""
        response = await async_client.get("/api/v1/agents/statistics/overview")
        assert response.status_code == 200

        stats = response.json()
        assert "total_agents" in stats
        assert "online_agents" in stats
        assert "active_agents" in stats  # Changed from offline_agents to active_agents
        assert isinstance(stats["total_agents"], int)
        assert isinstance(stats["online_agents"], int)
        assert isinstance(
            stats["active_agents"], int
        )  # Changed from offline_agents to active_agents

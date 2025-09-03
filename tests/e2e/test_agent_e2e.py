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
    async def test_agent_endpoints_require_auth(self, async_client: AsyncClient):
        """Test that agent endpoints require authentication."""
        # Test that agent registration requires authentication
        registration_data = {
            "name": "test_e2e_agent",
            "agent_type": "business_analyst",
            "version": "1.0.0",
            "capabilities": '["analysis"]',
            "configuration": '{"max_tasks": "5"}',
            "metadata_json": '{"test": "true"}',
            "description": "Test agent for e2e testing",
        }

        response = await async_client.post("/api/v1/agents/", json=registration_data)
        assert response.status_code == 401  # Unauthorized

        # Test that getting agents requires authentication
        response = await async_client.get("/api/v1/agents/")
        assert response.status_code == 401  # Unauthorized

        # Test that getting online agents requires authentication
        response = await async_client.get("/api/v1/agents/online")
        assert response.status_code == 401  # Unauthorized

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

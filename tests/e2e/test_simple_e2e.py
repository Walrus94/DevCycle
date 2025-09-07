"""Simple end-to-end test to verify basic functionality."""

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSimpleE2E:
    """Simple e2e tests to verify basic functionality."""

    @pytest.mark.asyncio
    async def test_health_endpoint_works(self, async_client: AsyncClient):
        """Test that health endpoint works without authentication."""
        print("🔍 Testing health endpoint...")
        response = await async_client.get("/api/v1/health")
        print(f"📡 Health response status: {response.status_code}")
        print(f"📄 Health response text: {response.text}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_agent_endpoint_requires_auth(self, async_client: AsyncClient):
        """Test that agent endpoint requires authentication and returns 401."""
        print("🔍 Testing agent endpoint authentication requirement...")
        response = await async_client.get("/api/v1/acp/agents")
        print(f"📡 Agent response status: {response.status_code}")
        print(f"📄 Agent response text: {response.text}")
        assert response.status_code == 401

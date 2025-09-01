"""
End-to-end tests for health endpoints.

This module tests the health endpoints in a real environment
to ensure they work properly with the FastAPI app.
"""

import time

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.health
@pytest.mark.asyncio
class TestHealthEndpointsE2E:
    """Test health endpoints in end-to-end environment."""

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, async_client: AsyncClient):
        """Test basic health check endpoint."""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_detailed_health_check(self, async_client: AsyncClient):
        """Test detailed health check endpoint."""
        response = await async_client.get("/api/v1/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "metrics" in data
        assert "uptime" in data["metrics"]

    @pytest.mark.asyncio
    async def test_readiness_check(self, async_client: AsyncClient):
        """Test readiness check endpoint."""
        response = await async_client.get("/api/v1/health/ready")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_liveness_check(self, async_client: AsyncClient):
        """Test liveness check endpoint."""
        response = await async_client.get("/api/v1/health/live")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_health_endpoints_consistency(self, async_client: AsyncClient):
        """Test that all health endpoints return consistent data."""
        endpoints = [
            "/api/v1/health",
            "/api/v1/health/detailed",
            "/api/v1/health/ready",
            "/api/v1/health/live",
        ]

        for endpoint in endpoints:
            response = await async_client.get(endpoint)
            assert response.status_code == 200

            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "ready", "alive"]

    @pytest.mark.asyncio
    async def test_health_endpoints_performance(self, async_client: AsyncClient):
        """Test that health endpoints respond quickly."""
        endpoints = [
            "/api/v1/health",
            "/api/v1/health/detailed",
            "/api/v1/health/ready",
            "/api/v1/health/live",
        ]

        for endpoint in endpoints:
            start_time = time.time()
            response = await async_client.get(endpoint)
            end_time = time.time()

            assert response.status_code == 200
            response_time = end_time - start_time

            # Health endpoints should respond within 100ms
            assert (
                response_time < 0.1
            ), f"Health endpoint {endpoint} took {response_time:.3f}s"

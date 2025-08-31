"""
End-to-end tests for health endpoints.

This module tests the health endpoints in a real environment
to ensure they work properly with the FastAPI app.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.health
class TestHealthEndpointsE2E:
    """Test health endpoints in end-to-end environment."""

    def test_health_check_endpoint(self, client: TestClient):
        """Test basic health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_detailed_health_check(self, client: TestClient):
        """Test detailed health check endpoint."""
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "metrics" in data
        assert "uptime" in data["metrics"]

    def test_readiness_check(self, client: TestClient):
        """Test readiness check endpoint."""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "ready"

    def test_liveness_check(self, client: TestClient):
        """Test liveness check endpoint."""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "alive"

    def test_health_endpoints_consistency(self, client: TestClient):
        """Test that all health endpoints return consistent data."""
        endpoints = [
            "/api/v1/health",
            "/api/v1/health/detailed",
            "/api/v1/health/ready",
            "/api/v1/health/live",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200

            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "ready", "alive"]

    def test_health_endpoints_performance(self, client: TestClient):
        """Test that health endpoints respond quickly."""
        import time

        endpoints = [
            "/api/v1/health",
            "/api/v1/health/detailed",
            "/api/v1/health/ready",
            "/api/v1/health/live",
        ]

        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()

            assert response.status_code == 200
            response_time = end_time - start_time

            # Health endpoints should respond within 100ms
            assert (
                response_time < 0.1
            ), f"Health endpoint {endpoint} took {response_time:.3f}s"

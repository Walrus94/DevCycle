"""Tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient

from devcycle.api.app import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.mark.api
class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client: TestClient) -> None:
        """Test basic health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "DevCycle API"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data

    def test_detailed_health_check(self, client: TestClient) -> None:
        """Test detailed health check endpoint."""
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["service"] == "DevCycle API"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data
        assert "components" in data
        assert "metrics" in data

        # Check components
        components = data["components"]
        assert "api" in components
        assert "configuration" in components
        assert "logging" in components

        # Check metrics
        metrics = data["metrics"]
        assert "response_time_ms" in metrics

    def test_readiness_check(self, client: TestClient) -> None:
        """Test readiness check endpoint."""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == "DevCycle API"
        assert "timestamp" in data
        assert "checks" in data

    def test_liveness_check(self, client: TestClient) -> None:
        """Test liveness check endpoint."""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "alive"
        assert data["service"] == "DevCycle API"
        assert "timestamp" in data

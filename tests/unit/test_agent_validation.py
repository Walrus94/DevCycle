"""Test agent model validation with XSS protection."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from devcycle.core.agents.models import AgentRegistration


class TestAgentValidation:
    """Test agent model validation with XSS protection."""

    def setup_method(self):
        """Set up test app."""
        self.app = FastAPI()

        @self.app.post("/agents")
        async def register_agent(registration: AgentRegistration):
            return {
                "message": "Agent registered successfully",
                "agent": registration.model_dump(),
            }

        self.client = TestClient(self.app)

    def test_valid_agent_registration(self):
        """Test registering an agent with valid data."""
        response = self.client.post(
            "/agents",
            json={
                "name": "Test Agent",
                "agent_type": "business_analyst",
                "description": "A test agent for validation",
                "version": "1.0.0",
                "capabilities": [],
                "configuration": None,
                "metadata": {},
            },
        )
        assert response.status_code == 200
        assert "Agent registered successfully" in response.json()["message"]

    def test_xss_protection_in_name(self):
        """Test XSS protection in agent name."""
        response = self.client.post(
            "/agents",
            json={
                "name": "<script>alert('xss')</script>",
                "agent_type": "business_analyst",
                "description": "Valid description",
                "version": "1.0.0",
                "capabilities": [],
                "configuration": None,
                "metadata": {},
            },
        )
        assert response.status_code == 422  # Validation error
        assert "Potentially dangerous content detected" in str(response.json())

    def test_xss_protection_in_description(self):
        """Test XSS protection in agent description."""
        response = self.client.post(
            "/agents",
            json={
                "name": "Test Agent",
                "agent_type": "business_analyst",
                "description": "<iframe src='javascript:alert(1)'></iframe>",
                "version": "1.0.0",
                "capabilities": [],
                "configuration": None,
                "metadata": {},
            },
        )
        assert response.status_code == 422  # Validation error
        assert "Potentially dangerous content detected" in str(response.json())

    def test_xss_protection_in_version(self):
        """Test XSS protection in agent version."""
        response = self.client.post(
            "/agents",
            json={
                "name": "Test Agent",
                "agent_type": "business_analyst",
                "description": "Valid description",
                "version": "1.0javascript:",  # XSS pattern that fits length limit
                "capabilities": [],
                "configuration": None,
                "metadata": {},
            },
        )
        assert response.status_code == 422  # Validation error
        assert "Potentially dangerous content detected" in str(response.json())

    def test_sql_injection_protection(self):
        """Test SQL injection protection."""
        response = self.client.post(
            "/agents",
            json={
                "name": "Test'; DROP TABLE agents; --",
                "agent_type": "business_analyst",
                "description": "Valid description",
                "version": "1.0.0",
                "capabilities": [],
                "configuration": None,
                "metadata": {},
            },
        )
        assert response.status_code == 422  # Validation error
        assert "Potentially dangerous SQL pattern detected" in str(response.json())

    def test_name_length_validation(self):
        """Test FastAPI's built-in length validation for name."""
        response = self.client.post(
            "/agents",
            json={
                "name": "",  # Too short
                "agent_type": "business_analyst",
                "description": "Valid description",
                "version": "1.0.0",
                "capabilities": [],
                "configuration": None,
                "metadata": {},
            },
        )
        assert response.status_code == 422  # Validation error
        assert "name" in str(response.json()).lower()

    def test_description_length_validation(self):
        """Test FastAPI's built-in length validation for description."""
        long_description = "x" * 501  # Too long
        response = self.client.post(
            "/agents",
            json={
                "name": "Test Agent",
                "agent_type": "business_analyst",
                "description": long_description,
                "version": "1.0.0",
                "capabilities": [],
                "configuration": None,
                "metadata": {},
            },
        )
        assert response.status_code == 422  # Validation error
        assert "description" in str(response.json()).lower()

    def test_version_length_validation(self):
        """Test FastAPI's built-in length validation for version."""
        long_version = "x" * 21  # Too long
        response = self.client.post(
            "/agents",
            json={
                "name": "Test Agent",
                "agent_type": "business_analyst",
                "description": "Valid description",
                "version": long_version,
                "capabilities": [],
                "configuration": None,
                "metadata": {},
            },
        )
        assert response.status_code == 422  # Validation error
        assert "version" in str(response.json()).lower()

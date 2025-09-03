"""Test FastAPI built-in validation with XSS protection."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, field_validator

from devcycle.core.validation.input import XSSValidator


class SecureUserCreate(BaseModel):
    """Example of using the XSS validator in a FastAPI model."""

    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name", "description")
    @classmethod
    def validate_no_xss(cls, v):
        """Validate that input contains no XSS attacks."""
        if v:
            return XSSValidator.validate_no_xss(v)
        return v

    @field_validator("name", "description")
    @classmethod
    def validate_no_sql_injection(cls, v):
        """Validate that input contains no SQL injection attempts."""
        if v:
            return XSSValidator.validate_no_sql_injection(v)
        return v


class TestFastAPIValidation:
    """Test FastAPI built-in validation with XSS protection."""

    def setup_method(self):
        """Set up test app."""
        self.app = FastAPI()

        @self.app.post("/users")
        async def create_user(user: SecureUserCreate):
            return {"message": "User created successfully", "user": user.model_dump()}

        self.client = TestClient(self.app)

    def test_valid_user_creation(self):
        """Test creating a user with valid data."""
        response = self.client.post(
            "/users",
            json={
                "name": "John Doe",
                "email": "john@example.com",
                "description": "A valid user description",
            },
        )
        assert response.status_code == 200
        assert "User created successfully" in response.json()["message"]

    def test_xss_protection_in_name(self):
        """Test XSS protection in name field."""
        response = self.client.post(
            "/users",
            json={
                "name": "<script>alert('xss')</script>",
                "email": "john@example.com",
                "description": "Valid description",
            },
        )
        assert response.status_code == 422  # Validation error
        assert "Potentially dangerous content detected" in str(response.json())

    def test_xss_protection_in_description(self):
        """Test XSS protection in description field."""
        response = self.client.post(
            "/users",
            json={
                "name": "John Doe",
                "email": "john@example.com",
                "description": "<iframe src='javascript:alert(1)'></iframe>",
            },
        )
        assert response.status_code == 422  # Validation error
        assert "Potentially dangerous content detected" in str(response.json())

    def test_sql_injection_protection(self):
        """Test SQL injection protection."""
        response = self.client.post(
            "/users",
            json={
                "name": "John'; DROP TABLE users; --",
                "email": "john@example.com",
                "description": "Valid description",
            },
        )
        assert response.status_code == 422  # Validation error
        assert "Potentially dangerous SQL pattern detected" in str(response.json())

    def test_invalid_email_format(self):
        """Test FastAPI's built-in email validation."""
        response = self.client.post(
            "/users",
            json={
                "name": "John Doe",
                "email": "invalid-email",
                "description": "Valid description",
            },
        )
        assert response.status_code == 422  # Validation error
        assert "email" in str(response.json()).lower()

    def test_name_length_validation(self):
        """Test FastAPI's built-in length validation."""
        response = self.client.post(
            "/users",
            json={
                "name": "",  # Too short
                "email": "john@example.com",
                "description": "Valid description",
            },
        )
        assert response.status_code == 422  # Validation error
        assert "name" in str(response.json()).lower()

    def test_description_length_validation(self):
        """Test FastAPI's built-in length validation for description."""
        long_description = "x" * 501  # Too long
        response = self.client.post(
            "/users",
            json={
                "name": "John Doe",
                "email": "john@example.com",
                "description": long_description,
            },
        )
        assert response.status_code == 422  # Validation error
        assert "description" in str(response.json()).lower()

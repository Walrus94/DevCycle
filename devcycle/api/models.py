"""
Common API response models for standardized responses.

This module provides standardized response models that ensure consistency
across all API endpoints.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standardized API response wrapper.

    This provides a consistent response format across all endpoints.
    """

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[T] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Human-readable message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response timestamp",
    )
    request_id: Optional[str] = Field(None, description="Unique request identifier")


class ErrorResponse(BaseModel):
    """
    Standardized error response.

    This provides a consistent error format across all endpoints.
    """

    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Error timestamp",
    )
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    path: Optional[str] = Field(None, description="Request path that caused the error")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standardized paginated response.

    This provides a consistent format for paginated data.
    """

    success: bool = Field(True, description="Whether the request was successful")
    data: List[T] = Field(..., description="List of items")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    message: Optional[str] = Field(None, description="Human-readable message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response timestamp",
    )
    request_id: Optional[str] = Field(None, description="Unique request identifier")


class HealthResponse(BaseModel):
    """
    Standardized health check response.

    This provides a consistent format for health check endpoints.
    """

    status: str = Field(
        ...,
        description="Overall health status",
        examples=["healthy", "degraded", "unhealthy"],
    )
    service: str = Field(..., description="Service name", examples=["DevCycle API"])
    version: str = Field(..., description="Service version", examples=["0.1.0"])
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Check timestamp",
    )
    components: Optional[Dict[str, str]] = Field(
        None,
        description="Component health status",
        examples=[{"api": "healthy", "configuration": "healthy", "logging": "healthy"}],
    )
    metrics: Optional[Dict[str, Any]] = Field(
        None,
        description="Health metrics",
        examples=[{"response_time_ms": 15.2, "uptime": "2d 5h 30m"}],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "service": "DevCycle API",
                "version": "0.1.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "components": {
                    "api": "healthy",
                    "configuration": "healthy",
                    "logging": "healthy",
                },
                "metrics": {"response_time_ms": 15.2, "uptime": "2d 5h 30m"},
            }
        }
    }


class UserContext(BaseModel):
    """
    User context information for authenticated requests.

    This provides user information that can be included in responses.
    """

    user_id: UUID = Field(..., description="User identifier")
    email: str = Field(..., description="User email")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")
    is_verified: bool = Field(..., description="Whether user is verified")

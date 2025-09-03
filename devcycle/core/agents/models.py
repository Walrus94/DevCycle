"""
Agent models and enums for DevCycle.

This module provides enums and data classes for agent-related functionality.
"""

from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ..validation.input import XSSValidator


class AgentStatus(str, Enum):
    """Agent status enumeration."""

    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class AgentCapability(str, Enum):
    """Agent capability enumeration."""

    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    ANALYSIS = "analysis"
    MONITORING = "monitoring"
    COMMUNICATION = "communication"
    TEXT_PROCESSING = "text_processing"


class AgentType(str, Enum):
    """Agent type enumeration."""

    CODE_GENERATOR = "code_generator"
    TESTER = "tester"
    DEPLOYER = "deployer"
    ANALYZER = "analyzer"
    MONITOR = "monitor"
    COMMUNICATOR = "communicator"
    BUSINESS_ANALYST = "business_analyst"
    DEVELOPER = "developer"


class AgentRegistration(BaseModel):
    """Agent registration data model."""

    name: str = Field(..., description="Agent name", min_length=1, max_length=100)
    agent_type: str = Field(..., description="Agent type", min_length=1, max_length=50)
    description: Optional[str] = Field(
        None, description="Agent description", max_length=500
    )
    version: str = Field(..., description="Agent version", min_length=1, max_length=20)
    capabilities: List[AgentCapability] = Field(..., description="Agent capabilities")
    configuration: Dict[str, str] = Field(
        default_factory=dict, description="Agent configuration"
    )
    metadata: Dict[str, str] = Field(default_factory=dict, description="Agent metadata")

    @field_validator("name", "agent_type", "description", "version")
    @classmethod
    def validate_no_xss(cls, v: str | None) -> str | None:
        """Validate that string fields don't contain XSS patterns."""
        if v is not None:
            result = XSSValidator.validate_no_xss(v)
            return str(result)
        return v

    @field_validator("name", "agent_type", "description", "version")
    @classmethod
    def validate_no_sql_injection(cls, v: str | None) -> str | None:
        """Validate that string fields don't contain SQL injection patterns."""
        if v is not None:
            result = XSSValidator.validate_no_sql_injection(v)
            return str(result)
        return v


class AgentConfiguration(BaseModel):
    """Agent configuration model."""

    name: str = Field(..., description="Configuration name")
    value: str = Field(..., description="Configuration value")
    description: Optional[str] = Field(None, description="Configuration description")
    is_required: bool = Field(
        False, description="Whether this configuration is required"
    )


class AgentInfo(BaseModel):
    """Agent information model."""

    id: UUID = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")
    agent_type: str = Field(..., description="Agent type")
    description: Optional[str] = Field(None, description="Agent description")
    version: str = Field(..., description="Agent version")
    capabilities: List[AgentCapability] = Field(..., description="Agent capabilities")
    status: AgentStatus = Field(..., description="Agent status")
    is_active: bool = Field(..., description="Whether agent is active")
    last_heartbeat: Optional[str] = Field(None, description="Last heartbeat timestamp")
    response_time_ms: Optional[int] = Field(
        None, description="Response time in milliseconds"
    )
    error_count: int = Field(0, description="Error count")
    uptime_seconds: int = Field(0, description="Uptime in seconds")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

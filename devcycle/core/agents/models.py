"""
Agent models for DevCycle.

This module defines the data models for agent management, including
agent registration, status tracking, configuration, and health monitoring.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ..database.models import Base


class AgentStatus(str, Enum):
    """Agent status enumeration."""

    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class AgentType(str, Enum):
    """Agent type enumeration."""

    BUSINESS_ANALYST = "business_analyst"
    DEVELOPER = "developer"
    TESTER = "tester"
    DEPLOYER = "deployer"
    MONITOR = "monitor"
    CUSTOM = "custom"


class AgentCapability(str, Enum):
    """Agent capability enumeration."""

    TEXT_PROCESSING = "text_processing"
    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    ANALYSIS = "analysis"
    PLANNING = "planning"


class AgentHealth(BaseModel):
    """Agent health status model."""

    status: AgentStatus
    last_heartbeat: datetime
    response_time_ms: Optional[int] = None
    error_count: int = 0
    last_error: Optional[str] = None
    uptime_seconds: int = 0


class AgentConfiguration(BaseModel):
    """Agent configuration model."""

    max_concurrent_tasks: int = 1
    timeout_seconds: int = 300
    retry_attempts: int = 3
    priority: int = 1
    capabilities: List[AgentCapability] = []
    settings: Dict[str, Any] = {}


class AgentRegistration(BaseModel):
    """Agent registration request model."""

    name: str = Field(..., min_length=1, max_length=100)
    agent_type: AgentType
    description: Optional[str] = Field(None, max_length=500)
    version: str = Field(..., min_length=1, max_length=20)
    capabilities: List[AgentCapability] = []
    configuration: Optional[AgentConfiguration] = None
    metadata: Dict[str, Any] = {}


class AgentUpdate(BaseModel):
    """Agent update request model."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    version: Optional[str] = Field(None, min_length=1, max_length=20)
    capabilities: Optional[List[AgentCapability]] = None
    configuration: Optional[AgentConfiguration] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Agent response model."""

    id: UUID
    name: str
    agent_type: AgentType
    description: Optional[str]
    version: str
    capabilities: List[AgentCapability]
    configuration: AgentConfiguration
    status: AgentStatus
    health: AgentHealth
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentHeartbeat(BaseModel):
    """Agent heartbeat model."""

    agent_id: UUID
    status: AgentStatus
    current_task: Optional[str] = None
    resource_usage: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class AgentTaskRequest(BaseModel):
    """Agent task request model."""

    id: UUID
    agent_id: UUID
    task_type: str
    status: str
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class AgentTaskResponse(BaseModel):
    """Agent task response model."""

    id: UUID
    agent_id: UUID
    task_type: str
    status: str
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# SQLAlchemy Models
class Agent(Base):
    """Agent database model."""

    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    capabilities: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    configuration: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Health tracking
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', type='{self.agent_type}')>"


class AgentTask(Base):
    """Agent task database model."""

    __tablename__ = "agent_tasks"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    agent_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    parameters: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<AgentTask(id={self.id}, type='{self.task_type}', "
            f"status='{self.status}')>"
        )

"""
Pydantic schemas for Tortoise ORM models.

These schemas provide request/response models for FastAPI endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AgentBase(BaseModel):
    """Base agent schema."""

    name: str
    agent_type: str
    description: Optional[str] = None
    version: str
    capabilities: str
    configuration: str
    metadata_json: str
    status: str = "offline"
    is_active: bool = True


class AgentCreate(AgentBase):
    """Schema for creating an agent."""

    pass


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: Optional[str] = None
    agent_type: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    capabilities: Optional[str] = None
    configuration: Optional[str] = None
    metadata_json: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class AgentResponse(AgentBase):
    """Schema for agent responses."""

    id: UUID
    last_heartbeat: Optional[datetime] = None
    response_time_ms: Optional[int] = None
    error_count: int
    last_error: Optional[str] = None
    uptime_seconds: int
    created_at: datetime
    updated_at: datetime
    last_seen: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AgentTaskBase(BaseModel):
    """Base agent task schema."""

    task_type: str
    status: str
    parameters: str
    result: Optional[str] = None
    error: Optional[str] = None


class AgentTaskCreate(AgentTaskBase):
    """Schema for creating an agent task."""

    agent_id: UUID


class AgentTaskResponse(AgentTaskBase):
    """Schema for agent task responses."""

    id: UUID
    agent_id: UUID
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

"""
Tortoise ORM models for DevCycle agents.

Simple, clean models with Django-like syntax.
"""

from uuid import uuid4

from tortoise import fields
from tortoise.models import Model


class Agent(Model):
    """Agent model using Tortoise ORM."""

    # Primary key
    id = fields.UUIDField(primary_key=True, default=uuid4)

    # Basic agent information
    name = fields.CharField(max_length=100, unique=True, db_index=True)
    agent_type = fields.CharField(max_length=50, db_index=True)
    description = fields.TextField(null=True)
    version = fields.CharField(max_length=20)

    # Configuration (stored as JSON strings)
    capabilities = fields.TextField()  # JSON string
    configuration = fields.TextField()  # JSON string
    metadata_json = fields.TextField()  # JSON string

    # Status and activity
    status = fields.CharField(max_length=20, default="offline")
    is_active = fields.BooleanField(default=True)

    # Health tracking
    last_heartbeat = fields.DatetimeField(null=True)
    response_time_ms = fields.IntField(null=True)
    error_count = fields.IntField(default=0)
    last_error = fields.TextField(null=True)
    uptime_seconds = fields.IntField(default=0)

    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_seen = fields.DatetimeField(null=True)

    # Relationships
    tasks: fields.ReverseRelation["AgentTask"]

    class Meta:
        """Meta class for Agent model."""

        table = "agents"

    def __str__(self) -> str:
        """Return string representation of Agent."""
        return f"Agent({self.name})"


class AgentTask(Model):
    """Agent task model using Tortoise ORM."""

    # Primary key
    id = fields.UUIDField(primary_key=True, default=uuid4)

    # Foreign key
    agent: fields.ForeignKeyRelation[Agent] = fields.ForeignKeyField(
        "models.Agent", related_name="tasks", db_index=True
    )

    # Task information
    task_type = fields.CharField(max_length=100, db_index=True)
    status = fields.CharField(max_length=50, db_index=True)
    parameters = fields.TextField()  # JSON string
    result = fields.TextField(null=True)  # JSON string
    error = fields.TextField(null=True)

    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)

    class Meta:
        """Meta class for AgentTask model."""

        table = "agent_tasks"

    def __str__(self) -> str:
        """Return string representation of AgentTask."""
        return f"AgentTask({self.task_type})"

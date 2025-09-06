"""
ACP Database Models for DevCycle.

This module defines Tortoise ORM models for ACP agent management,
workflow orchestration, and message logging.
"""

import uuid
from typing import Any

from tortoise import fields
from tortoise.models import Model


class ACPAgent(Model):
    """ACP agent database model."""

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    agent_id = fields.CharField(max_length=100, unique=True, db_index=True)
    name = fields.CharField(max_length=200)
    capabilities = fields.JSONField()
    status = fields.CharField(max_length=50, default="offline")
    last_heartbeat = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        """Tortoise ORM model metadata for ACPAgent."""

        table = "acp_agents"
        table_description = "ACP agent registry"


class ACPWorkflow(Model):
    """ACP workflow database model."""

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    workflow_id = fields.CharField(max_length=100, unique=True, db_index=True)
    name = fields.CharField(max_length=200)
    version = fields.CharField(max_length=50, default="1.0.0")
    status = fields.CharField(max_length=50, default="pending")
    steps = fields.JSONField(null=True, default=list)
    result = fields.JSONField(null=True)
    error = fields.TextField(null=True)
    retry_count = fields.IntField(default=0)
    max_retries = fields.IntField(default=3)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        """Tortoise ORM model metadata for ACPWorkflow."""

        table = "acp_workflows"
        table_description = "ACP workflow definitions and execution history"


class ACPWorkflowStep(Model):
    """ACP workflow step database model."""

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    workflow: Any = fields.ForeignKeyField(
        "models.ACPWorkflow", related_name="workflow_steps", on_delete=fields.CASCADE
    )
    step_id = fields.CharField(max_length=100, db_index=True)
    step_name = fields.CharField(max_length=200)
    agent_id = fields.CharField(max_length=100)
    status = fields.CharField(max_length=50, default="pending")
    input_data = fields.JSONField(default=dict)
    output_data = fields.JSONField(null=True)
    error = fields.TextField(null=True)
    retry_count = fields.IntField(default=0)
    max_retries = fields.IntField(default=3)
    depends_on = fields.JSONField(default=list)
    started_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        """Tortoise ORM model metadata for ACPWorkflowStep."""

        table = "acp_workflow_steps"
        table_description = "ACP workflow step execution details"


class ACPMessageLog(Model):
    """ACP message log database model."""

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    message_id = fields.CharField(max_length=100, db_index=True)
    from_agent = fields.CharField(max_length=100, null=True)
    to_agent = fields.CharField(max_length=100, null=True)
    message_type = fields.CharField(max_length=100)
    content = fields.JSONField()
    response = fields.JSONField(null=True)
    workflow_id = fields.CharField(max_length=100, null=True, db_index=True)
    success = fields.BooleanField(default=True)
    error = fields.TextField(null=True)
    processing_time_ms = fields.FloatField(null=True)
    timestamp = fields.DatetimeField(auto_now_add=True)

    class Meta:
        """Tortoise ORM model metadata for ACPMessageLog."""

        table = "acp_message_logs"
        table_description = "ACP message communication logs"


class ACPAgentMetrics(Model):
    """ACP agent metrics database model."""

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    agent_id = fields.CharField(max_length=100, db_index=True)
    metric_name = fields.CharField(max_length=100)
    metric_value = fields.FloatField()
    metric_unit = fields.CharField(max_length=50, null=True)
    metadata = fields.JSONField(default=dict)
    timestamp = fields.DatetimeField(auto_now_add=True)

    class Meta:
        """Database metadata for ACPAgentMetric."""

        table = "acp_agent_metrics"
        table_description = "ACP agent performance metrics"


class ACPWorkflowMetrics(Model):
    """ACP workflow metrics database model."""

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    workflow_id = fields.CharField(max_length=100, db_index=True)
    metric_name = fields.CharField(max_length=100)
    metric_value = fields.FloatField()
    metric_unit = fields.CharField(max_length=50, null=True)
    metadata = fields.JSONField(default=dict)
    timestamp = fields.DatetimeField(auto_now_add=True)

    class Meta:
        """Database metadata for ACPWorkflowMetrics."""

        table = "acp_workflow_metrics"
        table_description = "ACP workflow performance metrics"


class ACPSystemMetrics(Model):
    """ACP system metrics database model."""

    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    metric_name = fields.CharField(max_length=100, db_index=True)
    metric_value = fields.FloatField()
    metric_unit = fields.CharField(max_length=50, null=True)
    metadata = fields.JSONField(default=dict)
    timestamp = fields.DatetimeField(auto_now_add=True)

    class Meta:
        """Database metadata for ACPSystemMetrics."""

        table = "acp_system_metrics"
        table_description = "ACP system-wide performance metrics"

"""
ACP Persistence Layer.

This module provides the integration between ACP protocol models
and our Tortoise ORM persistence layer. ACP itself is ORM-agnostic,
so we handle the conversion between ACP models and database models.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from acp_sdk.models import AgentManifest, Message

from ..models.acp_models import (
    ACPAgent,
    ACPAgentMetrics,
    ACPMessageLog,
    ACPSystemMetrics,
    ACPWorkflow,
    ACPWorkflowMetrics,
    ACPWorkflowStep,
)
from .models import ACPAgentInfo, ACPMessage, ACPResponse
from .models import ACPWorkflow as ACPWorkflowModel


class ACPPersistenceManager:
    """Manages persistence for ACP protocol data."""

    def __init__(self) -> None:
        """Initialize the persistence manager."""
        self.logger = None  # Will be set by the service

    async def save_agent_from_manifest(
        self, manifest: AgentManifest, agent_id: str
    ) -> ACPAgent:
        """Save an agent from ACP AgentManifest to database."""
        agent = await ACPAgent.create(
            agent_id=agent_id,
            name=manifest.name,
            capabilities=(
                getattr(manifest.metadata, "capabilities", [])
                if hasattr(manifest.metadata, "capabilities")
                else []
            ),
            status="offline",  # Will be updated when agent comes online
            last_heartbeat=None,
        )
        return agent

    async def save_agent_from_info(self, agent_info: ACPAgentInfo) -> ACPAgent:
        """Save an agent from our ACPAgentInfo to database."""
        agent = await ACPAgent.create(
            agent_id=agent_info.agent_id,
            name=agent_info.agent_name,
            capabilities=agent_info.capabilities,
            status=agent_info.status.value,
            last_heartbeat=(
                datetime.now(timezone.utc)
                if agent_info.status.value == "online"
                else None
            ),
        )
        return agent

    async def update_agent_status(self, agent_id: str, status: str) -> bool:
        """Update agent status in database."""
        try:
            agent = await ACPAgent.get(agent_id=agent_id)
            agent.status = status
            if status == "online":
                agent.last_heartbeat = datetime.now(timezone.utc)
            await agent.save()
            return True
        except Exception:
            return False

    async def log_message(
        self,
        message: ACPMessage,
        response: Optional[ACPResponse] = None,
        workflow_id: Optional[str] = None,
    ) -> ACPMessageLog:
        """Log an ACP message exchange to database."""
        log = await ACPMessageLog.create(
            message_id=message.message_id,
            from_agent=message.source_agent_id,
            to_agent=message.target_agent_id,
            message_type=message.message_type,
            content=message.content,
            response=response.content if response else None,
            workflow_id=workflow_id,
            success=response.success if response else False,
            error=response.error if response and not response.success else None,
            processing_time_ms=response.processing_time_ms if response else None,
        )
        return log

    async def log_acp_message(
        self,
        acp_message: Message,
        response: Optional[Dict] = None,
        workflow_id: Optional[str] = None,
    ) -> ACPMessageLog:
        """Log an ACP SDK Message to database."""
        # Convert ACP SDK Message to our format for logging
        content = {}
        if acp_message.parts:
            content = {"parts": [part.model_dump() for part in acp_message.parts]}

        log = await ACPMessageLog.create(
            message_id=str(uuid.uuid4()),
            from_agent=None,  # ACP SDK doesn't track source agent
            to_agent=None,  # ACP SDK doesn't track target agent
            message_type=acp_message.role,
            content=content,
            response=response,
            workflow_id=workflow_id,
            success=response is not None,
            error=None,
            processing_time_ms=None,
        )
        return log

    async def save_workflow(self, workflow: ACPWorkflowModel) -> ACPWorkflow:
        """Save an ACP workflow to database."""
        db_workflow = await ACPWorkflow.create(
            workflow_id=workflow.workflow_id,
            name=workflow.workflow_name,
            version=workflow.workflow_version,
            status=workflow.status,
            steps=[step.model_dump() for step in workflow.steps],
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
        )

        # Save workflow steps
        for step in workflow.steps:
            await ACPWorkflowStep.create(
                workflow=db_workflow,
                step_id=step.step_id,
                step_name=step.step_name,
                agent_id=step.agent_id,
                status=step.status,
                input_data=step.input_data,
                output_data=step.output_data,
                error=step.error,
                retry_count=step.retry_count,
                max_retries=step.max_retries,
                depends_on=step.depends_on,
                started_at=step.started_at,
                completed_at=step.completed_at,
            )

        return db_workflow

    async def load_workflow(self, workflow_id: str) -> Optional[ACPWorkflowModel]:
        """Load an ACP workflow from database."""
        try:
            db_workflow = await ACPWorkflow.get(workflow_id=workflow_id)
            db_steps = await ACPWorkflowStep.filter(workflow=db_workflow).all()

            # Convert database workflow to ACP model
            from .models import ACPWorkflowStep as ACPWorkflowStepModel

            steps = []
            for db_step in db_steps:
                step = ACPWorkflowStepModel(
                    step_id=db_step.step_id,
                    step_name=db_step.step_name,
                    agent_id=db_step.agent_id,
                    status=db_step.status,
                    input_data=db_step.input_data,
                    output_data=db_step.output_data,
                    error=db_step.error,
                    retry_count=db_step.retry_count,
                    max_retries=db_step.max_retries,
                    depends_on=db_step.depends_on,
                    started_at=db_step.started_at,
                    completed_at=db_step.completed_at,
                )
                steps.append(step)

            workflow = ACPWorkflowModel(
                workflow_id=db_workflow.workflow_id,
                workflow_name=db_workflow.name,
                workflow_version=db_workflow.version,
                status=db_workflow.status,
                steps=steps,
                started_at=db_workflow.started_at,
                completed_at=db_workflow.completed_at,
            )

            return workflow

        except Exception:
            return None

    async def record_agent_metric(
        self,
        agent_id: str,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ACPAgentMetrics:
        """Record a metric for an agent."""
        return await ACPAgentMetrics.create(
            agent_id=agent_id,
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit=metric_unit,
            metadata=metadata or {},
        )

    async def record_workflow_metric(
        self,
        workflow_id: str,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ACPWorkflowMetrics:
        """Record a metric for a workflow."""
        return await ACPWorkflowMetrics.create(
            workflow_id=workflow_id,
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit=metric_unit,
            metadata=metadata or {},
        )

    async def record_system_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ACPSystemMetrics:
        """Record a system-wide metric."""
        return await ACPSystemMetrics.create(
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit=metric_unit,
            metadata=metadata or {},
        )

    async def get_agent_metrics(
        self,
        agent_id: str,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[ACPAgentMetrics]:
        """Get metrics for an agent."""
        query = ACPAgentMetrics.filter(agent_id=agent_id)

        if metric_name:
            query = query.filter(metric_name=metric_name)

        if start_time:
            query = query.filter(timestamp__gte=start_time)

        if end_time:
            query = query.filter(timestamp__lte=end_time)

        return await query.order_by("-timestamp").all()

    async def get_workflow_metrics(
        self, workflow_id: str, metric_name: Optional[str] = None
    ) -> List[ACPWorkflowMetrics]:
        """Get metrics for a workflow."""
        query = ACPWorkflowMetrics.filter(workflow_id=workflow_id)

        if metric_name:
            query = query.filter(metric_name=metric_name)

        return await query.order_by("-timestamp").all()

    async def get_system_metrics(
        self,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[ACPSystemMetrics]:
        """Get system-wide metrics."""
        query = ACPSystemMetrics.all()

        if metric_name:
            query = query.filter(metric_name=metric_name)

        if start_time:
            query = query.filter(timestamp__gte=start_time)

        if end_time:
            query = query.filter(timestamp__lte=end_time)

        return await query.order_by("-timestamp").all()

    async def cleanup_old_metrics(self, days_to_keep: int = 30) -> int:
        """Clean up old metrics to prevent database bloat."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        # Count records to be deleted
        agent_count = await ACPAgentMetrics.filter(timestamp__lt=cutoff_date).count()
        workflow_count = await ACPWorkflowMetrics.filter(
            timestamp__lt=cutoff_date
        ).count()
        system_count = await ACPSystemMetrics.filter(timestamp__lt=cutoff_date).count()

        # Delete old records
        await ACPAgentMetrics.filter(timestamp__lt=cutoff_date).delete()
        await ACPWorkflowMetrics.filter(timestamp__lt=cutoff_date).delete()
        await ACPSystemMetrics.filter(timestamp__lt=cutoff_date).delete()

        return agent_count + workflow_count + system_count

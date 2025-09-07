"""
ACP Workflow Engine service.

Handles workflow orchestration and multi-agent coordination.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...cache.acp_cache import ACPCache
from ..config import ACPConfig, ACPWorkflowConfig
from ..events.redis_events import RedisACPEvents
from ..models import (
    ACPMessage,
    ACPMessageType,
    ACPResponse,
    ACPWorkflow,
    ACPWorkflowStep,
)
from .agent_registry import ACPAgentRegistry
from .message_router import ACPMessageRouter

logger = logging.getLogger(__name__)


class ACPWorkflowEngine:
    """ACP workflow orchestration engine for DevCycle."""

    def __init__(
        self,
        config: ACPConfig,
        workflow_config: ACPWorkflowConfig,
        agent_registry: ACPAgentRegistry,
        message_router: ACPMessageRouter,
        acp_cache: Optional[ACPCache] = None,
        events: Optional[RedisACPEvents] = None,
    ):
        """Initialize the workflow engine."""
        self.config = config
        self.workflow_config = workflow_config
        self.agent_registry = agent_registry
        self.message_router = message_router
        self.acp_cache = acp_cache
        self.events = events

        # Workflow state
        self.active_workflows: Dict[str, ACPWorkflow] = {}
        self.completed_workflows: Dict[str, ACPWorkflow] = {}
        self.failed_workflows: Dict[str, ACPWorkflow] = {}

        # Workflow execution tasks
        self.workflow_tasks: Dict[str, asyncio.Task] = {}

        # Statistics
        self.stats = {
            "active_workflows": 0,
            "completed_workflows": 0,
            "failed_workflows": 0,
            "total_steps_executed": 0,
            "avg_workflow_duration_ms": 0.0,
        }

    async def start_workflow(self, workflow: ACPWorkflow) -> ACPResponse:
        """Start a new workflow execution."""
        try:
            # Validate workflow
            if not self._validate_workflow(workflow):
                return ACPResponse(
                    response_id=f"resp_workflow_{workflow.workflow_id}",
                    message_id=f"workflow_{workflow.workflow_id}",
                    success=False,
                    error="Invalid workflow definition",
                    error_code="INVALID_WORKFLOW",
                )

            # Check if workflow already exists
            if workflow.workflow_id in self.active_workflows:
                return ACPResponse(
                    response_id=f"resp_workflow_{workflow.workflow_id}",
                    message_id=f"workflow_{workflow.workflow_id}",
                    success=False,
                    error="Workflow already running",
                    error_code="WORKFLOW_ALREADY_RUNNING",
                )

            # Initialize workflow state
            workflow.status = "running"
            workflow.started_at = datetime.now(timezone.utc)
            self.active_workflows[workflow.workflow_id] = workflow

            # Cache workflow state in Redis if available
            if self.acp_cache:
                await self.acp_cache.cache_workflow_state(
                    workflow.workflow_id,
                    {
                        "status": "running",
                        "current_step": (
                            workflow.steps[0].step_id if workflow.steps else None
                        ),
                        "progress": 0,
                        "started_at": workflow.started_at.isoformat(),
                        "total_steps": len(workflow.steps),
                        "completed_steps": 0,
                    },
                )

            # Start workflow execution task
            task = asyncio.create_task(self._execute_workflow(workflow))
            self.workflow_tasks[workflow.workflow_id] = task

            # Publish workflow started event
            if self.events:
                await self.events.publish_workflow_started(
                    workflow.workflow_id,
                    {
                        "workflow_name": workflow.workflow_name,
                        "total_steps": len(workflow.steps),
                        "started_at": workflow.started_at.isoformat(),
                    },
                )

            logger.info(f"Started workflow {workflow.workflow_id}")

            return ACPResponse(
                response_id=f"resp_workflow_{workflow.workflow_id}",
                message_id=f"workflow_{workflow.workflow_id}",
                success=True,
                content={
                    "workflow_id": workflow.workflow_id,
                    "status": "started",
                    "total_steps": len(workflow.steps),
                },
            )

        except Exception as e:
            logger.error(f"Failed to start workflow {workflow.workflow_id}: {e}")
            return ACPResponse(
                response_id=f"resp_workflow_{workflow.workflow_id}",
                message_id=f"workflow_{workflow.workflow_id}",
                success=False,
                error=f"Workflow start error: {str(e)}",
                error_code="WORKFLOW_START_ERROR",
            )

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a workflow."""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": workflow.status,
                "started_at": (
                    workflow.started_at.isoformat() if workflow.started_at else None
                ),
                "completed_steps": len(
                    [s for s in workflow.steps if s.status == "completed"]
                ),
                "total_steps": len(workflow.steps),
                "current_step": self._get_current_step(workflow),
            }

        if workflow_id in self.completed_workflows:
            workflow = self.completed_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": workflow.status,
                "started_at": (
                    workflow.started_at.isoformat() if workflow.started_at else None
                ),
                "completed_at": (
                    workflow.completed_at.isoformat() if workflow.completed_at else None
                ),
                "total_steps": len(workflow.steps),
            }

        if workflow_id in self.failed_workflows:
            workflow = self.failed_workflows[workflow_id]
            return {
                "workflow_id": workflow_id,
                "status": workflow.status,
                "started_at": (
                    workflow.started_at.isoformat() if workflow.started_at else None
                ),
                "error": workflow.error,
                "total_steps": len(workflow.steps),
            }

        return None

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        try:
            if workflow_id not in self.active_workflows:
                logger.warning(f"Workflow {workflow_id} not found for cancellation")
                return False

            # Cancel workflow task
            if workflow_id in self.workflow_tasks:
                task = self.workflow_tasks[workflow_id]
                task.cancel()
                del self.workflow_tasks[workflow_id]

            # Update workflow status
            workflow = self.active_workflows[workflow_id]
            workflow.status = "cancelled"
            workflow.completed_at = datetime.now(timezone.utc)

            # Move to completed workflows
            del self.active_workflows[workflow_id]
            self.completed_workflows[workflow_id] = workflow

            logger.info(f"Cancelled workflow {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
            return False

    async def retry_workflow(self, workflow_id: str) -> ACPResponse:
        """Retry a failed workflow."""
        try:
            if workflow_id not in self.failed_workflows:
                return ACPResponse(
                    response_id=f"resp_workflow_{workflow_id}",
                    message_id=f"workflow_{workflow_id}",
                    success=False,
                    error="Workflow not found in failed workflows",
                    error_code="WORKFLOW_NOT_FOUND",
                )

            workflow = self.failed_workflows[workflow_id]

            # Check retry limit
            if workflow.retry_count >= workflow.max_retries:
                return ACPResponse(
                    response_id=f"resp_workflow_{workflow_id}",
                    message_id=f"workflow_{workflow_id}",
                    success=False,
                    error="Maximum retry attempts exceeded",
                    error_code="MAX_RETRIES_EXCEEDED",
                )

            # Reset workflow state
            workflow.status = "pending"
            workflow.error = None
            workflow.retry_count += 1
            workflow.started_at = None
            workflow.completed_at = None

            # Reset all steps
            for step in workflow.steps:
                step.status = "pending"
                step.started_at = None
                step.completed_at = None
                step.error = None

            # Remove from failed workflows
            del self.failed_workflows[workflow_id]

            # Start workflow again
            return await self.start_workflow(workflow)

        except Exception as e:
            logger.error(f"Failed to retry workflow {workflow_id}: {e}")
            return ACPResponse(
                response_id=f"resp_workflow_{workflow_id}",
                message_id=f"workflow_{workflow_id}",
                success=False,
                error=f"Workflow retry error: {str(e)}",
                error_code="WORKFLOW_RETRY_ERROR",
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get workflow engine statistics."""
        return self.stats.copy()

    def _validate_workflow(self, workflow: ACPWorkflow) -> bool:
        """Validate workflow definition."""
        try:
            # Check required fields
            if not workflow.workflow_id or not workflow.workflow_name:
                return False

            # Check steps
            if not workflow.steps:
                return False

            # Validate each step
            for step in workflow.steps:
                if not step.step_id or not step.step_name or not step.agent_id:
                    return False

            # Check for circular dependencies
            if self._has_circular_dependencies(workflow.steps):
                return False

            return True

        except Exception as e:
            logger.error(f"Workflow validation error: {e}")
            return False

    def _has_circular_dependencies(self, steps: List[ACPWorkflowStep]) -> bool:
        """Check for circular dependencies in workflow steps."""
        # Simple cycle detection using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(step_id: str) -> bool:
            if step_id in rec_stack:
                return True
            if step_id in visited:
                return False

            visited.add(step_id)
            rec_stack.add(step_id)

            step = next((s for s in steps if s.step_id == step_id), None)
            if step:
                for dep in step.depends_on:
                    if has_cycle(dep):
                        return True

            rec_stack.remove(step_id)
            return False

        for step in steps:
            if has_cycle(step.step_id):
                return True

        return False

    def _get_current_step(self, workflow: ACPWorkflow) -> Optional[str]:
        """Get the current executing step."""
        for step in workflow.steps:
            if step.status == "running":
                return step.step_id
        return None

    async def _execute_workflow(self, workflow: ACPWorkflow) -> None:
        """Execute a workflow."""
        try:
            logger.info(f"Executing workflow {workflow.workflow_id}")

            # Execute steps based on coordination strategy
            if self.workflow_config.coordination_strategy == "sequential":
                await self._execute_sequential(workflow)
            elif self.workflow_config.coordination_strategy == "parallel":
                await self._execute_parallel(workflow)
            else:
                await self._execute_sequential(workflow)  # Default to sequential

            # Mark workflow as completed
            workflow.status = "completed"
            workflow.completed_at = datetime.now(timezone.utc)

            # Update Redis cache with completion status
            if self.acp_cache:
                await self.acp_cache.cache_workflow_state(
                    workflow.workflow_id,
                    {
                        "status": "completed",
                        "current_step": None,
                        "progress": 100,
                        "started_at": (
                            workflow.started_at.isoformat()
                            if workflow.started_at
                            else None
                        ),
                        "completed_at": workflow.completed_at.isoformat(),
                        "total_steps": len(workflow.steps),
                        "completed_steps": len(workflow.steps),
                        "duration_ms": (
                            (
                                workflow.completed_at - workflow.started_at
                            ).total_seconds()
                            * 1000
                            if workflow.started_at
                            else 0
                        ),
                    },
                )

            # Publish workflow completed event
            if self.events:
                await self.events.publish_workflow_completed(
                    workflow.workflow_id,
                    {
                        "workflow_name": workflow.workflow_name,
                        "total_steps": len(workflow.steps),
                        "duration_ms": (
                            (
                                workflow.completed_at - workflow.started_at
                            ).total_seconds()
                            * 1000
                            if workflow.started_at
                            else 0
                        ),
                        "completed_at": workflow.completed_at.isoformat(),
                    },
                )

            # Move to completed workflows
            del self.active_workflows[workflow.workflow_id]
            self.completed_workflows[workflow.workflow_id] = workflow

            logger.info(f"Completed workflow {workflow.workflow_id}")

        except Exception as e:
            logger.error(f"Workflow execution error: {e}")

            # Mark workflow as failed
            workflow.status = "failed"
            workflow.error = str(e)
            workflow.completed_at = datetime.now(timezone.utc)

            # Update Redis cache with failure status
            if self.acp_cache:
                await self.acp_cache.cache_workflow_state(
                    workflow.workflow_id,
                    {
                        "status": "failed",
                        "current_step": None,
                        "progress": 0,
                        "started_at": (
                            workflow.started_at.isoformat()
                            if workflow.started_at
                            else None
                        ),
                        "completed_at": workflow.completed_at.isoformat(),
                        "error": str(e),
                        "total_steps": len(workflow.steps),
                        "completed_steps": 0,
                        "duration_ms": (
                            (
                                workflow.completed_at - workflow.started_at
                            ).total_seconds()
                            * 1000
                            if workflow.started_at
                            else 0
                        ),
                    },
                )

            # Publish workflow failed event
            if self.events:
                await self.events.publish_workflow_failed(workflow.workflow_id, str(e))

            # Move to failed workflows
            del self.active_workflows[workflow.workflow_id]
            self.failed_workflows[workflow.workflow_id] = workflow

        finally:
            # Clean up task
            if workflow.workflow_id in self.workflow_tasks:
                del self.workflow_tasks[workflow.workflow_id]

    async def _execute_sequential(self, workflow: ACPWorkflow) -> None:
        """Execute workflow steps sequentially."""
        # Sort steps by dependencies
        sorted_steps = self._topological_sort(workflow.steps)

        for step in sorted_steps:
            await self._execute_step(workflow, step)

    async def _execute_parallel(self, workflow: ACPWorkflow) -> None:
        """Execute workflow steps in parallel where possible."""
        # Group steps by dependency level
        dependency_levels = self._group_by_dependency_level(workflow.steps)

        for level_steps in dependency_levels:
            if self.workflow_config.parallel_execution and len(level_steps) > 1:
                # Execute steps in parallel
                tasks = [self._execute_step(workflow, step) for step in level_steps]
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Execute steps sequentially
                for step in level_steps:
                    await self._execute_step(workflow, step)

    async def _execute_step(self, workflow: ACPWorkflow, step: ACPWorkflowStep) -> None:
        """Execute a single workflow step."""
        try:
            logger.info(
                f"Executing step {step.step_id} in workflow {workflow.workflow_id}"
            )

            # Update step status
            step.status = "running"
            step.started_at = datetime.now(timezone.utc)

            # Create message for the step
            message = ACPMessage(
                message_id=f"step_{step.step_id}_{workflow.workflow_id}",
                message_type=ACPMessageType.REQUEST,  # Use valid ACP message type
                content={
                    "step_name": step.step_name,
                    "step_data": step.input_data,
                    "workflow_id": workflow.workflow_id,
                    "step_id": step.step_id,
                },
                target_agent_id=step.agent_id,
                workflow_id=workflow.workflow_id,
            )

            # Send message to agent
            response = await self.message_router.route_workflow_message(
                message, workflow.workflow_id
            )

            if response.success:
                # Update step with response
                step.output_data = response.content
                step.status = "completed"
                step.completed_at = datetime.now(timezone.utc)

                # Cache step result in Redis if available
                if self.acp_cache:
                    await self.acp_cache.update_workflow_step(
                        workflow.workflow_id,
                        step.step_id,
                        {
                            "status": "completed",
                            "result": step.output_data,
                            "duration_ms": (
                                step.completed_at - step.started_at
                            ).total_seconds()
                            * 1000,
                            "agent_id": step.agent_id,
                            "completed_at": step.completed_at.isoformat(),
                        },
                    )

                # Publish step completed event
                if self.events:
                    await self.events.publish_workflow_step_completed(
                        workflow.workflow_id, step.step_id, step.output_data
                    )

                logger.info(f"Completed step {step.step_id}")
            else:
                # Handle step failure
                step.status = "failed"
                step.error = response.error
                step.completed_at = datetime.now(timezone.utc)

                # Publish step failed event
                if self.events:
                    await self.events.publish_workflow_step_failed(
                        workflow.workflow_id,
                        step.step_id,
                        response.error or "Unknown error",
                    )

                # Cache step failure in Redis if available
                if self.acp_cache:
                    await self.acp_cache.update_workflow_step(
                        workflow.workflow_id,
                        step.step_id,
                        {
                            "status": "failed",
                            "error": step.error,
                            "duration_ms": (
                                step.completed_at - step.started_at
                            ).total_seconds()
                            * 1000,
                            "agent_id": step.agent_id,
                            "completed_at": step.completed_at.isoformat(),
                        },
                    )

                logger.error(f"Failed step {step.step_id}: {response.error}")

                # Retry if configured
                if (
                    self.workflow_config.retry_failed_steps
                    and step.retry_count < step.max_retries
                ):
                    step.retry_count += 1
                    step.status = "pending"
                    await self._execute_step(workflow, step)
                else:
                    raise Exception(f"Step {step.step_id} failed: {response.error}")

        except Exception as e:
            logger.error(f"Step execution error: {e}")
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now(timezone.utc)
            raise e

    def _topological_sort(self, steps: List[ACPWorkflowStep]) -> List[ACPWorkflowStep]:
        """Sort steps by dependencies using topological sort."""
        # Simple implementation - in practice, you'd want a more robust algorithm
        sorted_steps: List[ACPWorkflowStep] = []
        remaining_steps = steps.copy()

        while remaining_steps:
            # Find steps with no unresolved dependencies
            ready_steps = []
            for step in remaining_steps:
                if not step.depends_on or all(
                    dep in [s.step_id for s in sorted_steps] for dep in step.depends_on
                ):
                    ready_steps.append(step)

            if not ready_steps:
                # Circular dependency or error
                break

            # Add ready steps to sorted list
            for step in ready_steps:
                sorted_steps.append(step)
                remaining_steps.remove(step)

        return sorted_steps

    def _group_by_dependency_level(
        self, steps: List[ACPWorkflowStep]
    ) -> List[List[ACPWorkflowStep]]:
        """Group steps by dependency level for parallel execution."""
        levels = []
        remaining_steps = steps.copy()
        completed_steps: set[str] = set()

        while remaining_steps:
            # Find steps that can be executed at this level
            current_level = []
            for step in remaining_steps[:]:
                if not step.depends_on or all(
                    dep in completed_steps for dep in step.depends_on
                ):
                    current_level.append(step)
                    remaining_steps.remove(step)

            if not current_level:
                # No more steps can be executed
                break

            levels.append(current_level)
            completed_steps.update(step.step_id for step in current_level)

        return levels

    async def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow state from Redis cache if available."""
        if self.acp_cache:
            return await self.acp_cache.get_workflow_state(workflow_id)
        return None

    async def get_workflow_step_result(
        self, workflow_id: str, step_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get workflow step result from Redis cache if available."""
        if self.acp_cache:
            return await self.acp_cache.get_workflow_step(workflow_id, step_id)
        return None

    async def update_workflow_progress(
        self, workflow_id: str, current_step: str, progress: int
    ) -> None:
        """Update workflow progress in Redis cache if available."""
        if self.acp_cache:
            # Get current state
            current_state = await self.acp_cache.get_workflow_state(workflow_id)
            if current_state:
                current_state.update(
                    {"current_step": current_step, "progress": progress}
                )
                await self.acp_cache.cache_workflow_state(workflow_id, current_state)

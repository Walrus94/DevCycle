"""
Agent lifecycle and state management for DevCycle.

This module defines the comprehensive lifecycle management system for agents,
including state transitions, lifecycle operations, and state persistence.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID

from ..logging import get_logger


class AgentLifecycleState(str, Enum):
    """Agent lifecycle states."""

    # Initial states
    REGISTERED = "registered"  # Agent registered but not deployed
    DEPLOYING = "deploying"  # Agent being deployed
    DEPLOYED = "deployed"  # Agent deployed but not active

    # Active states
    STARTING = "starting"  # Agent starting up
    ONLINE = "online"  # Agent online and ready
    BUSY = "busy"  # Agent processing tasks
    IDLE = "idle"  # Agent online but no active tasks

    # Transitional states
    STOPPING = "stopping"  # Agent shutting down
    UPDATING = "updating"  # Agent being updated
    SCALING = "scaling"  # Agent being scaled

    # Error states
    ERROR = "error"  # Agent in error state
    FAILED = "failed"  # Agent failed to start/operate
    TIMEOUT = "timeout"  # Agent timeout

    # Maintenance states
    MAINTENANCE = "maintenance"  # Agent in maintenance mode
    SUSPENDED = "suspended"  # Agent suspended
    OFFLINE = "offline"  # Agent offline

    # Final states
    TERMINATED = "terminated"  # Agent terminated
    DELETED = "deleted"  # Agent deleted


class AgentExecutionState(str, Enum):
    """Agent execution states (for individual tasks)."""

    PENDING = "pending"  # Task queued
    RUNNING = "running"  # Task executing
    COMPLETED = "completed"  # Task completed successfully
    FAILED = "failed"  # Task failed
    CANCELLED = "cancelled"  # Task cancelled
    TIMEOUT = "timeout"  # Task timed out


@dataclass
class AgentStateTransition:
    """Represents a state transition for an agent."""

    from_state: AgentLifecycleState
    to_state: AgentLifecycleState
    timestamp: datetime
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    triggered_by: Optional[str] = None  # User, system, agent, etc.


@dataclass
class AgentLifecycleEvent:
    """Represents a lifecycle event for an agent."""

    event_type: str
    agent_id: UUID
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"  # system, user, agent, external


class AgentLifecycleManager:
    """
    Manages agent lifecycle and state transitions.

    This class handles the complete lifecycle of agents from registration
    to termination, including state transitions, event handling, and
    lifecycle operations.
    """

    # Define valid state transitions
    VALID_TRANSITIONS: Dict[AgentLifecycleState, Set[AgentLifecycleState]] = {
        # From REGISTERED
        AgentLifecycleState.REGISTERED: {
            AgentLifecycleState.DEPLOYING,
            AgentLifecycleState.DELETED,
        },
        # From DEPLOYING
        AgentLifecycleState.DEPLOYING: {
            AgentLifecycleState.DEPLOYED,
            AgentLifecycleState.FAILED,
            AgentLifecycleState.ERROR,
        },
        # From DEPLOYED
        AgentLifecycleState.DEPLOYED: {
            AgentLifecycleState.STARTING,
            AgentLifecycleState.UPDATING,
            AgentLifecycleState.DELETED,
        },
        # From STARTING
        AgentLifecycleState.STARTING: {
            AgentLifecycleState.ONLINE,
            AgentLifecycleState.FAILED,
            AgentLifecycleState.ERROR,
            AgentLifecycleState.TIMEOUT,
        },
        # From ONLINE
        AgentLifecycleState.ONLINE: {
            AgentLifecycleState.BUSY,
            AgentLifecycleState.IDLE,
            AgentLifecycleState.STOPPING,
            AgentLifecycleState.UPDATING,
            AgentLifecycleState.MAINTENANCE,
            AgentLifecycleState.SUSPENDED,
            AgentLifecycleState.OFFLINE,
            AgentLifecycleState.ERROR,
        },
        # From BUSY
        AgentLifecycleState.BUSY: {
            AgentLifecycleState.IDLE,
            AgentLifecycleState.ONLINE,
            AgentLifecycleState.STOPPING,
            AgentLifecycleState.MAINTENANCE,
            AgentLifecycleState.SUSPENDED,
            AgentLifecycleState.OFFLINE,
            AgentLifecycleState.ERROR,
        },
        # From IDLE
        AgentLifecycleState.IDLE: {
            AgentLifecycleState.BUSY,
            AgentLifecycleState.ONLINE,
            AgentLifecycleState.STOPPING,
            AgentLifecycleState.UPDATING,
            AgentLifecycleState.MAINTENANCE,
            AgentLifecycleState.SUSPENDED,
            AgentLifecycleState.OFFLINE,
            AgentLifecycleState.ERROR,
        },
        # From STOPPING
        AgentLifecycleState.STOPPING: {
            AgentLifecycleState.OFFLINE,
            AgentLifecycleState.TERMINATED,
            AgentLifecycleState.ERROR,
        },
        # From UPDATING
        AgentLifecycleState.UPDATING: {
            AgentLifecycleState.ONLINE,
            AgentLifecycleState.FAILED,
            AgentLifecycleState.ERROR,
        },
        # From SCALING
        AgentLifecycleState.SCALING: {
            AgentLifecycleState.ONLINE,
            AgentLifecycleState.BUSY,
            AgentLifecycleState.IDLE,
            AgentLifecycleState.ERROR,
        },
        # From ERROR
        AgentLifecycleState.ERROR: {
            AgentLifecycleState.ONLINE,
            AgentLifecycleState.OFFLINE,
            AgentLifecycleState.MAINTENANCE,
            AgentLifecycleState.FAILED,
        },
        # From FAILED
        AgentLifecycleState.FAILED: {
            AgentLifecycleState.STARTING,
            AgentLifecycleState.DEPLOYING,
            AgentLifecycleState.DELETED,
        },
        # From TIMEOUT
        AgentLifecycleState.TIMEOUT: {
            AgentLifecycleState.OFFLINE,
            AgentLifecycleState.ERROR,
            AgentLifecycleState.STARTING,
        },
        # From MAINTENANCE
        AgentLifecycleState.MAINTENANCE: {
            AgentLifecycleState.ONLINE,
            AgentLifecycleState.OFFLINE,
            AgentLifecycleState.SUSPENDED,
        },
        # From SUSPENDED
        AgentLifecycleState.SUSPENDED: {
            AgentLifecycleState.ONLINE,
            AgentLifecycleState.MAINTENANCE,
            AgentLifecycleState.OFFLINE,
        },
        # From OFFLINE
        AgentLifecycleState.OFFLINE: {
            AgentLifecycleState.STARTING,
            AgentLifecycleState.MAINTENANCE,
            AgentLifecycleState.TERMINATED,
            AgentLifecycleState.DELETED,
        },
        # From TERMINATED
        AgentLifecycleState.TERMINATED: {
            AgentLifecycleState.DELETED,
        },
        # From DELETED (final state)
        AgentLifecycleState.DELETED: set(),
    }

    def __init__(
        self,
        agent_id: UUID,
        initial_state: AgentLifecycleState = AgentLifecycleState.REGISTERED,
    ):
        """Initialize the lifecycle manager for an agent."""
        self.agent_id = agent_id
        self.current_state = initial_state
        self.state_history: List[AgentStateTransition] = []
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.logger = get_logger(f"agent.lifecycle.{agent_id}")

        # Record initial state
        self._record_state_transition(
            from_state=AgentLifecycleState.REGISTERED,  # Virtual initial state
            to_state=initial_state,
            reason="Initial state",
            triggered_by="system",
        )

        self.logger.info(
            f"Agent lifecycle manager initialized with state: {initial_state}"
        )

    def can_transition_to(self, target_state: AgentLifecycleState) -> bool:
        """Check if transition to target state is valid."""
        return target_state in self.VALID_TRANSITIONS.get(self.current_state, set())

    def get_valid_transitions(self) -> Set[AgentLifecycleState]:
        """Get all valid transitions from current state."""
        return self.VALID_TRANSITIONS.get(self.current_state, set())

    async def transition_to(
        self,
        target_state: AgentLifecycleState,
        reason: str = "State transition",
        triggered_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Transition agent to target state.

        Args:
            target_state: Target state to transition to
            reason: Reason for the transition
            triggered_by: Who/what triggered the transition
            metadata: Additional metadata for the transition

        Returns:
            True if transition was successful, False otherwise
        """
        if not self.can_transition_to(target_state):
            self.logger.warning(
                f"Invalid state transition from {self.current_state} to {target_state}"
            )
            return False

        try:
            # Emit pre-transition event
            await self._emit_event(
                "pre_transition",
                {
                    "from_state": self.current_state,
                    "to_state": target_state,
                    "reason": reason,
                    "triggered_by": triggered_by,
                    "metadata": metadata or {},
                },
            )

            # Record the transition
            self._record_state_transition(
                from_state=self.current_state,
                to_state=target_state,
                reason=reason,
                triggered_by=triggered_by,
                metadata=metadata or {},
            )

            # Update current state
            previous_state = self.current_state
            self.current_state = target_state

            # Emit post-transition event
            await self._emit_event(
                "post_transition",
                {
                    "from_state": previous_state,
                    "to_state": target_state,
                    "reason": reason,
                    "triggered_by": triggered_by,
                    "metadata": metadata or {},
                },
            )

            self.logger.info(
                f"Agent transitioned from {previous_state} to {target_state}: {reason}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to transition to {target_state}: {e}")
            return False

    def _record_state_transition(
        self,
        from_state: AgentLifecycleState,
        to_state: AgentLifecycleState,
        reason: str,
        triggered_by: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a state transition in history."""
        transition = AgentStateTransition(
            from_state=from_state,
            to_state=to_state,
            timestamp=datetime.now(timezone.utc),
            reason=reason,
            metadata=metadata or {},
            triggered_by=triggered_by,
        )
        self.state_history.append(transition)

    def on_event(self, event_type: str, handler: Callable) -> None:
        """Register an event handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to registered handlers."""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_type, data)
                    else:
                        handler(event_type, data)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event_type}: {e}")

    def get_state_history(
        self, limit: Optional[int] = None
    ) -> List[AgentStateTransition]:
        """Get state transition history."""
        if limit is None:
            return self.state_history.copy()
        return self.state_history[-limit:]

    def get_current_state_info(self) -> Dict[str, Any]:
        """Get current state information."""
        return {
            "agent_id": str(self.agent_id),
            "current_state": self.current_state,
            "valid_transitions": list(self.get_valid_transitions()),
            "state_history_count": len(self.state_history),
            "last_transition": (
                self.state_history[-1].__dict__ if self.state_history else None
            ),
        }

    def is_operational(self) -> bool:
        """Check if agent is in an operational state."""
        operational_states = {
            AgentLifecycleState.ONLINE,
            AgentLifecycleState.BUSY,
            AgentLifecycleState.IDLE,
        }
        return self.current_state in operational_states

    def is_available_for_tasks(self) -> bool:
        """Check if agent is available for new tasks."""
        available_states = {AgentLifecycleState.ONLINE, AgentLifecycleState.IDLE}
        return self.current_state in available_states

    def is_in_error_state(self) -> bool:
        """Check if agent is in an error state."""
        error_states = {
            AgentLifecycleState.ERROR,
            AgentLifecycleState.FAILED,
            AgentLifecycleState.TIMEOUT,
        }
        return self.current_state in error_states

    def is_in_maintenance(self) -> bool:
        """Check if agent is in maintenance mode."""
        maintenance_states = {
            AgentLifecycleState.MAINTENANCE,
            AgentLifecycleState.SUSPENDED,
            AgentLifecycleState.UPDATING,
        }
        return self.current_state in maintenance_states


class AgentLifecycleService:
    """
    Service for managing agent lifecycles across the system.

    This service provides high-level operations for agent lifecycle management,
    including deployment, activation, deactivation, and monitoring.
    """

    def __init__(self) -> None:
        """Initialize the lifecycle service."""
        self.managers: Dict[UUID, AgentLifecycleManager] = {}
        self.logger = get_logger("agent.lifecycle.service")

    def get_manager(self, agent_id: UUID) -> AgentLifecycleManager:
        """Get or create a lifecycle manager for an agent."""
        if agent_id not in self.managers:
            self.managers[agent_id] = AgentLifecycleManager(agent_id)
        return self.managers[agent_id]

    async def register_agent(self, agent_id: UUID) -> bool:
        """Register a new agent."""
        manager = self.get_manager(agent_id)

        # If already registered, return True
        if manager.current_state == AgentLifecycleState.REGISTERED:
            return True

        return await manager.transition_to(
            AgentLifecycleState.REGISTERED,
            reason="Agent registered",
            triggered_by="system",
        )

    async def deploy_agent(self, agent_id: UUID) -> bool:
        """Deploy an agent."""
        manager = self.get_manager(agent_id)

        # Transition through deployment states
        if not await manager.transition_to(
            AgentLifecycleState.DEPLOYING,
            reason="Starting deployment",
            triggered_by="system",
        ):
            return False

        # Simulate deployment process
        await asyncio.sleep(1)  # Simulate deployment time

        return await manager.transition_to(
            AgentLifecycleState.DEPLOYED,
            reason="Deployment completed",
            triggered_by="system",
        )

    async def start_agent(self, agent_id: UUID) -> bool:
        """Start an agent."""
        manager = self.get_manager(agent_id)

        if not await manager.transition_to(
            AgentLifecycleState.STARTING, reason="Starting agent", triggered_by="system"
        ):
            return False

        # Simulate startup process
        await asyncio.sleep(2)  # Simulate startup time

        return await manager.transition_to(
            AgentLifecycleState.ONLINE,
            reason="Agent started successfully",
            triggered_by="system",
        )

    async def stop_agent(self, agent_id: UUID) -> bool:
        """Stop an agent."""
        manager = self.get_manager(agent_id)

        if not await manager.transition_to(
            AgentLifecycleState.STOPPING, reason="Stopping agent", triggered_by="system"
        ):
            return False

        # Simulate shutdown process
        await asyncio.sleep(1)  # Simulate shutdown time

        return await manager.transition_to(
            AgentLifecycleState.OFFLINE, reason="Agent stopped", triggered_by="system"
        )

    async def assign_task(self, agent_id: UUID) -> bool:
        """Assign a task to an agent."""
        manager = self.get_manager(agent_id)

        if not manager.is_available_for_tasks():
            self.logger.warning(f"Agent {agent_id} not available for tasks")
            return False

        return await manager.transition_to(
            AgentLifecycleState.BUSY, reason="Task assigned", triggered_by="system"
        )

    async def complete_task(self, agent_id: UUID) -> bool:
        """Mark task as completed."""
        manager = self.get_manager(agent_id)

        if manager.current_state != AgentLifecycleState.BUSY:
            self.logger.warning(f"Agent {agent_id} not in BUSY state")
            return False

        return await manager.transition_to(
            AgentLifecycleState.IDLE, reason="Task completed", triggered_by="system"
        )

    async def put_in_maintenance(
        self, agent_id: UUID, reason: str = "Maintenance"
    ) -> bool:
        """Put agent in maintenance mode."""
        manager = self.get_manager(agent_id)

        return await manager.transition_to(
            AgentLifecycleState.MAINTENANCE, reason=reason, triggered_by="system"
        )

    async def resume_from_maintenance(self, agent_id: UUID) -> bool:
        """Resume agent from maintenance mode."""
        manager = self.get_manager(agent_id)

        if manager.current_state != AgentLifecycleState.MAINTENANCE:
            self.logger.warning(f"Agent {agent_id} not in maintenance mode")
            return False

        return await manager.transition_to(
            AgentLifecycleState.ONLINE,
            reason="Resumed from maintenance",
            triggered_by="system",
        )

    async def handle_error(self, agent_id: UUID, error_message: str) -> bool:
        """Handle agent error."""
        manager = self.get_manager(agent_id)

        return await manager.transition_to(
            AgentLifecycleState.ERROR,
            reason=f"Error: {error_message}",
            triggered_by="system",
            metadata={"error_message": error_message},
        )

    def get_agent_status(self, agent_id: UUID) -> Optional[Dict[str, Any]]:
        """Get agent status."""
        if agent_id not in self.managers:
            return None

        manager = self.managers[agent_id]
        return manager.get_current_state_info()

    def get_all_agent_statuses(self) -> Dict[UUID, Dict[str, Any]]:
        """Get status of all agents."""
        return {
            agent_id: manager.get_current_state_info()
            for agent_id, manager in self.managers.items()
        }

    def get_operational_agents(self) -> List[UUID]:
        """Get list of operational agents."""
        return [
            agent_id
            for agent_id, manager in self.managers.items()
            if manager.is_operational()
        ]

    def get_available_agents(self) -> List[UUID]:
        """Get list of agents available for tasks."""
        return [
            agent_id
            for agent_id, manager in self.managers.items()
            if manager.is_available_for_tasks()
        ]

    def get_agents_in_error(self) -> List[UUID]:
        """Get list of agents in error state."""
        return [
            agent_id
            for agent_id, manager in self.managers.items()
            if manager.is_in_error_state()
        ]

    def get_agents_in_maintenance(self) -> List[UUID]:
        """Get list of agents in maintenance."""
        return [
            agent_id
            for agent_id, manager in self.managers.items()
            if manager.is_in_maintenance()
        ]

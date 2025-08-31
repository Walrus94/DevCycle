"""
Base agent framework for DevCycle AI agents.

This module defines the base classes and interfaces that all specialized
agents must implement, providing a consistent framework for agent development.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.config import get_config
from ..core.logging import get_logger, log_agent_activity


class AgentStatus(Enum):
    """Status of an agent execution."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentResult:
    """Result of an agent execution."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
        }


class BaseAgent(ABC):
    """
    Base class for all DevCycle AI agents.

    This class provides the common interface and functionality that all
    specialized agents must implement.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base agent.

        Args:
            name: Unique name for this agent
            config: Agent-specific configuration
        """
        self.name = name
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self.logger = get_logger(f"agent.{name}")
        self.execution_history: List[AgentResult] = []
        self.current_task: Optional[asyncio.Task] = None

        # Only load global config if config was explicitly provided (not None)
        # This preserves the test expectation of empty config by default
        if config is not None:
            self._load_config()

        self.logger.info(f"Agent {name} initialized")

    def _load_config(self) -> None:
        """Load agent configuration from global config."""
        global_config = get_config()
        agent_config = global_config.get_agent_config(self.name.lower())
        if agent_config:
            # Merge global config with existing config, preserving existing values
            # Since this method is only called when config is not None,
            # we can safely update
            for key, value in agent_config.items():
                if key not in self.config:
                    self.config[key] = value
            self.logger.debug(f"Loaded configuration: {agent_config}")

    @abstractmethod
    async def process(self, input_data: Any, **kwargs: Any) -> AgentResult:
        """
        Process input data and return results.

        This is the main method that all agents must implement.

        Args:
            input_data: Input data to process
            **kwargs: Additional parameters

        Returns:
            AgentResult containing the processing results
        """
        pass

    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input data before processing.

        Args:
            input_data: Input data to validate

        Returns:
            True if input is valid, False otherwise
        """
        pass

    async def execute(self, input_data: Any, **kwargs: Any) -> AgentResult:
        """
        Execute the agent with proper error handling and logging.

        Args:
            input_data: Input data to process
            **kwargs: Additional parameters

        Returns:
            AgentResult containing the execution results
        """
        start_time = time.time()

        try:
            # Validate input
            if not self.validate_input(input_data):
                error_msg = f"Invalid input data for agent {self.name}"
                self.logger.error(error_msg)
                self.status = AgentStatus.FAILED
                result = AgentResult(
                    success=False,
                    error=error_msg,
                    execution_time=time.time() - start_time,
                )
                # Store in history
                self.execution_history.append(result)
                return result

            # Update status
            self.status = AgentStatus.RUNNING
            log_agent_activity(
                self.name,
                "execution_started",
                "started",
                {"input_type": type(input_data).__name__},
            )

            # Process input
            result = await self.process(input_data, **kwargs)

            # Update execution time
            result.execution_time = time.time() - start_time

            # Update status
            self.status = AgentStatus.COMPLETED

            # Log success
            log_agent_activity(
                self.name,
                "execution_completed",
                "completed",
                {
                    "execution_time": result.execution_time,
                    "success": result.success,
                },
            )

            # Store in history
            self.execution_history.append(result)

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Agent {self.name} failed: {str(e)}"

            self.logger.error(error_msg, exc_info=True)
            self.status = AgentStatus.FAILED

            # Log failure
            log_agent_activity(
                self.name,
                "execution_failed",
                "failed",
                {"error": str(e), "execution_time": execution_time},
            )

            # Create error result
            result = AgentResult(
                success=False, error=error_msg, execution_time=execution_time
            )

            # Store in history
            self.execution_history.append(result)

            return result

    def execute_async(self, input_data: Any, **kwargs: Any) -> asyncio.Task:
        """
        Execute the agent asynchronously.

        Args:
            input_data: Input data to process
            **kwargs: Additional parameters

        Returns:
            Task object for the execution
        """
        if self.current_task and not self.current_task.done():
            raise RuntimeError(f"Agent {self.name} is already running")

        self.current_task = asyncio.create_task(self.execute(input_data, **kwargs))
        return self.current_task

    def cancel(self) -> bool:
        """
        Cancel the current execution.

        Returns:
            True if cancellation was successful, False otherwise
        """
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            self.status = AgentStatus.CANCELLED
            self.logger.info(f"Agent {self.name} execution cancelled")
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status.

        Returns:
            Dictionary containing agent status information
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "execution_history_count": len(self.execution_history),
            "last_execution": (
                (
                    self.execution_history[-1].to_dict()
                    if self.execution_history
                    else None
                )
            ),
            "config": self.config,
        }

    def get_execution_history(self, limit: Optional[int] = None) -> List[AgentResult]:
        """
        Get execution history.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of execution results
        """
        if limit is None:
            return self.execution_history.copy()
        return self.execution_history[-limit:]

    def reset(self) -> None:
        """Reset agent to initial state."""
        self.status = AgentStatus.IDLE
        self.execution_history.clear()
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        self.current_task = None
        self.logger.info(f"Agent {self.name} reset")

    def __str__(self) -> str:
        """Return string representation of the agent."""
        return (
            f"{self.__class__.__name__}"
            f"(name='{self.name}', status='{self.status.value}')"
        )

    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        return (
            f"{self.__class__.__name__}"
            f"(name='{self.name}', status='{self.status.value}', "
            f"config={self.config})"
        )


class AgentFactory:
    """Factory for creating agent instances."""

    _agents: Dict[str, type[BaseAgent]] = {}

    @classmethod
    def register(cls, name: str, agent_class: type[BaseAgent]) -> None:
        """Register an agent class."""
        if not issubclass(agent_class, BaseAgent):
            raise ValueError("Agent class must inherit from BaseAgent")
        cls._agents[name] = agent_class

    @classmethod
    def create(cls, name: str, agent_type: str, **kwargs: Any) -> BaseAgent:
        """Create an agent instance."""
        if agent_type not in cls._agents:
            raise ValueError(f"Unknown agent type: {agent_type}")

        agent_class = cls._agents[agent_type]
        return agent_class(name=name, **kwargs)

    @classmethod
    def list_agents(cls) -> List[str]:
        """List all registered agent types."""
        return list(cls._agents.keys())

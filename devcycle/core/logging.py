"""
Logging configuration for DevCycle system using structlog.

This module provides structured logging configuration optimized for Kibana integration
and production environments.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import structlog

from .config import get_config


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    json_output: bool = True,
) -> None:
    """
    Set up structured logging for DevCycle.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        json_output: Whether to output JSON logs (recommended for production)
    """
    config = get_config()

    # Set logging level
    log_level = level or config.logging.level

    # Configure structlog for structured logging
    processors: list[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add JSON renderer for production/Kibana compatibility
    if json_output or config.environment == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Human-readable format for development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Add file handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))

        # Use JSON format for file logging
        json_formatter = logging.Formatter("%(message)s")
        file_handler.setFormatter(json_formatter)

        logging.getLogger().addHandler(file_handler)

    # Log initialization
    logger = structlog.get_logger(__name__)
    logger.info(
        "Logging initialized",
        level=log_level,
        json_output=json_output,
        log_file=str(log_file) if log_file else None,
    )


def get_logger(name: str) -> Any:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


def log_agent_activity(
    agent_name: str,
    action: str,
    status: str = "started",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log agent activity with structured data.

    Args:
        agent_name: Name of the agent
        action: Action being performed
        status: Status of the action (started, completed, failed)
        details: Additional details about the action
    """
    logger = structlog.get_logger("agent_activity")

    log_data = {
        "agent": agent_name,
        "action": action,
        "status": status,
        "event_type": "agent_activity",
    }

    if details:
        log_data.update(details)

    if status == "started":
        logger.info("Agent activity started", **log_data)
    elif status == "completed":
        logger.info("Agent activity completed", **log_data)
    elif status == "failed":
        logger.error("Agent activity failed", **log_data)
    else:
        logger.info("Agent activity status", **log_data)


def log_workflow_step(
    workflow_id: str,
    step_name: str,
    step_number: int,
    total_steps: int,
    status: str = "started",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log workflow step execution with structured data.

    Args:
        workflow_id: Unique identifier for the workflow
        step_name: Name of the current step
        step_number: Current step number (1-based)
        total_steps: Total number of steps in workflow
        status: Status of the step (started, completed, failed)
        details: Additional details about the step
    """
    logger = structlog.get_logger("workflow")

    log_data = {
        "workflow_id": workflow_id,
        "step": step_name,
        "step_number": step_number,
        "total_steps": total_steps,
        "progress": f"{step_number}/{total_steps}",
        "status": status,
        "event_type": "workflow_step",
    }

    if details:
        log_data.update(details)

    if status == "started":
        logger.info("Workflow step started", **log_data)
    elif status == "completed":
        logger.info("Workflow step completed", **log_data)
    elif status == "failed":
        logger.error("Workflow step failed", **log_data)
    else:
        logger.info("Workflow step status", **log_data)


def log_performance(func_name: Optional[str] = None) -> Callable:
    """
    Decorator to log function performance with structured data.

    Args:
        func_name: Optional custom name for the function
    """

    def decorator(func: Callable) -> Callable:
        import functools
        import time

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            name = func_name or func.__name__
            logger = structlog.get_logger("performance")

            try:
                # Log function call
                logger.debug(
                    "Function call started",
                    function=name,
                    args_count=len(args),
                    kwargs_count=len(kwargs),
                    event_type="function_call",
                )

                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Log successful completion
                logger.info(
                    "Function completed",
                    function=name,
                    execution_time=execution_time,
                    success=True,
                    event_type="function_completion",
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                # Log error
                logger.error(
                    "Function failed",
                    function=name,
                    execution_time=execution_time,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    success=False,
                    event_type="function_error",
                )
                raise

        return wrapper

    return decorator


# Initialize logging when module is imported
setup_logging(json_output=True)

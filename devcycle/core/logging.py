"""
Logging configuration for DevCycle system using structlog.

This module provides structured logging configuration optimized for Kibana integration
and production environments.
"""

import logging
import sys
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import structlog

from .config import get_config


def _add_correlation_id(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add correlation ID for request tracing."""
    import contextvars

    # Try to get correlation ID from context
    correlation_id = getattr(contextvars, "_correlation_id", None)
    if correlation_id is not None:
        event_dict["correlation_id"] = correlation_id.get()
    else:
        # Generate a simple correlation ID if not available
        import uuid

        event_dict["correlation_id"] = str(uuid.uuid4())[:8]

    return event_dict


def _add_service_metadata(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add service metadata for better Kibana filtering."""
    config = get_config()

    event_dict.update(
        {
            "service_name": "devcycle",
            "service_version": "0.1.0",
            "environment": config.environment.value,
            "hostname": _get_hostname(),
        }
    )

    return event_dict


def _get_hostname() -> str:
    """Get hostname for logging."""
    import socket

    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


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
        # Add service information for better Kibana filtering
        structlog.processors.add_log_level,
        # Add correlation ID for request tracing
        _add_correlation_id,
        # Add service metadata
        _add_service_metadata,
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
    Log function performance with structured data.

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


# Security Logging Components


class SecurityEventType(Enum):
    """Types of security events to log."""

    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_BLOCKED = "auth_blocked"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ACCESS_DENIED = "access_denied"
    ADMIN_ACTION = "admin_action"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    ROLE_CHANGED = "role_changed"
    PASSWORD_CHANGED = "password_changed"  # nosec B105 - Not a hardcoded password
    LOGOUT = "logout"
    SESSION_EXPIRED = "session_expired"
    API_KEY_USED = "api_key_used"
    API_KEY_REVOKED = "api_key_revoked"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_ALERT = "security_alert"


class SecuritySeverity(Enum):
    """Security event severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityLogger:
    """Specialized logger for security events with structured data."""

    def __init__(self) -> None:
        """Initialize security logger."""
        self.logger = structlog.get_logger("security")
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure structured logging for security events."""
        # Security logging uses the same configuration as main logging
        pass

    def _get_client_info(self, request: Optional[Any] = None) -> Dict[str, Any]:
        """Extract client information from request."""
        if not request:
            return {}

        client_info = {}

        # Get client IP
        if hasattr(request, "client") and request.client:
            client_info["ip_address"] = request.client.host
        elif hasattr(request, "headers"):
            # Check for forwarded headers
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                client_info["ip_address"] = forwarded_for.split(",")[0].strip()
            else:
                client_info["ip_address"] = "unknown"

        # Get user agent
        if hasattr(request, "headers"):
            client_info["user_agent"] = request.headers.get("user-agent", "unknown")

        return client_info

    def _create_event_id(self) -> str:
        """Generate unique event ID."""
        return str(uuid.uuid4())

    def log_security_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: SecuritySeverity = SecuritySeverity.MEDIUM,
        request: Optional[Any] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Log a security event with structured data.

        Returns:
            str: Event ID for tracking
        """
        event_id = self._create_event_id()

        # Extract client info from request if provided
        if request:
            client_info = self._get_client_info(request)
            ip_address = ip_address or client_info.get("ip_address")
            user_agent = user_agent or client_info.get("user_agent")

        log_data = {
            "event_id": event_id,
            "event_type": event_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": severity.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
            "additional_context": additional_context or {},
        }

        # Log based on severity
        if severity == SecuritySeverity.CRITICAL:
            self.logger.critical("Security event", **log_data)
        elif severity == SecuritySeverity.HIGH:
            self.logger.error("Security event", **log_data)
        elif severity == SecuritySeverity.MEDIUM:
            self.logger.warning("Security event", **log_data)
        else:
            self.logger.info("Security event", **log_data)

        return event_id

    def log_auth_success(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request: Optional[Any] = None,
        additional_details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log successful authentication."""
        return self.log_security_event(
            SecurityEventType.AUTH_SUCCESS,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request=request,
            details=additional_details or {},
            severity=SecuritySeverity.LOW,
        )

    def log_auth_failure(
        self,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: str = "Invalid credentials",
        request: Optional[Any] = None,
        additional_details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log failed authentication attempt."""
        details = {"email": email, "reason": reason, **(additional_details or {})}

        return self.log_security_event(
            SecurityEventType.AUTH_FAILURE,
            ip_address=ip_address,
            user_agent=user_agent,
            request=request,
            details=details,
            severity=SecuritySeverity.MEDIUM,
        )

    def log_rate_limit_exceeded(
        self,
        ip_address: Optional[str] = None,
        endpoint: str = "unknown",
        user_id: Optional[str] = None,
        request: Optional[Any] = None,
        additional_details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log rate limit violations."""
        details = {"endpoint": endpoint, **(additional_details or {})}

        return self.log_security_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            ip_address=ip_address,
            request=request,
            details=details,
            severity=SecuritySeverity.MEDIUM,
        )

    def log_suspicious_activity(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        activity: str = "Unknown suspicious activity",
        request: Optional[Any] = None,
        additional_details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log suspicious user activity."""
        details = {"activity": activity, **(additional_details or {})}

        return self.log_security_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            ip_address=ip_address,
            request=request,
            details=details,
            severity=SecuritySeverity.HIGH,
        )


# Global security logger instance
security_logger = SecurityLogger()

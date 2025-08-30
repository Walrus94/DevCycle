"""
General error handling and retry mechanisms for DevCycle.

This module provides error categorization, retry strategies, and error
response handling that can be used across the entire system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorType(Enum):
    """Types of errors that can occur in the system."""

    VALIDATION_ERROR = "validation_error"  # Invalid input/data format
    PROCESSING_ERROR = "processing_error"  # Processing/execution failure
    TIMEOUT_ERROR = "timeout_error"  # Operation timeout
    RESOURCE_ERROR = "resource_error"  # Resource unavailable
    NETWORK_ERROR = "network_error"  # Communication failure
    AUTHENTICATION_ERROR = "authentication_error"  # Authentication failure
    AUTHORIZATION_ERROR = "authorization_error"  # Authorization failure
    CONFIGURATION_ERROR = "configuration_error"  # Configuration issue
    UNKNOWN_ERROR = "unknown_error"  # Unexpected errors


class RetryStrategy(Enum):
    """Retry strategies for failed operations."""

    IMMEDIATE = "immediate"  # Retry immediately
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # Wait 1s, 2s, 4s, 8s...
    LINEAR_BACKOFF = "linear_backoff"  # Wait 1s, 2s, 3s, 4s...
    CUSTOM = "custom"  # Custom retry schedule


@dataclass
class ErrorDetails:
    """Detailed error information for failed operations."""

    error_type: ErrorType
    error_code: str
    error_message: str
    error_context: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    max_retries: int = 3
    retry_after: Optional[datetime] = None
    retry_strategy: Optional[RetryStrategy] = None
    source: Optional[str] = None  # Where the error originated

    def can_retry(self) -> bool:
        """Check if this error can be retried."""
        return self.retry_count < self.max_retries and self.error_type in [
            ErrorType.PROCESSING_ERROR,
            ErrorType.TIMEOUT_ERROR,
            ErrorType.RESOURCE_ERROR,
            ErrorType.NETWORK_ERROR,
            ErrorType.AUTHENTICATION_ERROR,
            ErrorType.CONFIGURATION_ERROR,
        ]

    def should_retry_now(self) -> bool:
        """Check if it's time to retry."""
        if not self.can_retry():
            return False

        if self.retry_after is None:
            return True

        return datetime.now(timezone.utc) >= self.retry_after


class RetryHandler:
    """General-purpose retry logic handler."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    def calculate_retry_delay(
        self,
        retry_count: int,
        strategy: RetryStrategy,
        custom_delays: Optional[List[float]] = None,
    ) -> float:
        """Calculate delay before next retry."""
        if strategy == RetryStrategy.IMMEDIATE:
            return float(0.0)
        elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return float(self.base_delay * (2**retry_count))
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            return float(self.base_delay * (retry_count + 1))
        elif strategy == RetryStrategy.CUSTOM:
            if custom_delays is not None:
                delay_value = custom_delays[min(retry_count, len(custom_delays) - 1)]
                return float(delay_value)
            else:
                return float(self.base_delay)

    def prepare_for_retry(
        self, error_details: ErrorDetails, strategy: RetryStrategy
    ) -> ErrorDetails:
        """Prepare error details for retry."""
        if not error_details.can_retry():
            return error_details

        retry_count = error_details.retry_count + 1
        delay = self.calculate_retry_delay(retry_count, strategy)
        retry_after = datetime.now(timezone.utc) + timedelta(seconds=delay)

        return ErrorDetails(
            error_type=error_details.error_type,
            error_code=error_details.error_code,
            error_message=error_details.error_message,
            error_context=error_details.error_context,
            timestamp=error_details.timestamp,
            retry_count=retry_count,
            max_retries=error_details.max_retries,
            retry_after=retry_after,
            retry_strategy=strategy,
            source=error_details.source,
        )


# Convenience functions for creating error responses
def create_error_response(
    error_type: ErrorType,
    error_code: str,
    error_message: str,
    error_context: Optional[Dict[str, Any]] = None,
    retry_strategy: Optional[RetryStrategy] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """Create error response data structure."""
    return {
        "error_type": error_type.value,
        "error_code": error_code,
        "error_message": error_message,
        "error_context": error_context or {},
        "retry_strategy": retry_strategy.value if retry_strategy else None,
        "retry_count": 0,
        "max_retries": 3,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }


def is_retryable_error(error_type: ErrorType) -> bool:
    """Check if an error type is retryable."""
    return error_type in [
        ErrorType.PROCESSING_ERROR,
        ErrorType.TIMEOUT_ERROR,
        ErrorType.RESOURCE_ERROR,
        ErrorType.NETWORK_ERROR,
        ErrorType.AUTHENTICATION_ERROR,
        ErrorType.CONFIGURATION_ERROR,
    ]


def create_system_error(
    error_type: ErrorType,
    error_code: str,
    error_message: str,
    error_context: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
) -> ErrorDetails:
    """Create a system error with default settings."""
    return ErrorDetails(
        error_type=error_type,
        error_code=error_code,
        error_message=error_message,
        error_context=error_context or {},
        source=source,
    )

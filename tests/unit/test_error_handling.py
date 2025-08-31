"""
Tests for the error handling and retry mechanisms.
"""

from datetime import datetime, timedelta, timezone

import pytest

from devcycle.core import (
    ErrorDetails,
    ErrorType,
    RetryHandler,
    RetryStrategy,
    create_error_response,
    create_system_error,
    is_retryable_error,
)
from devcycle.core.protocols import MessageStatus, create_error_event


@pytest.mark.unit
class TestErrorHandling:
    """Test the error handling implementation."""

    def test_error_type_enum(self) -> None:
        """Test error type enum values."""
        assert ErrorType.VALIDATION_ERROR.value == "validation_error"
        assert ErrorType.PROCESSING_ERROR.value == "processing_error"
        assert ErrorType.TIMEOUT_ERROR.value == "timeout_error"
        assert ErrorType.RESOURCE_ERROR.value == "resource_error"
        assert ErrorType.NETWORK_ERROR.value == "network_error"
        assert ErrorType.UNKNOWN_ERROR.value == "unknown_error"

    def test_retry_strategy_enum(self) -> None:
        """Test retry strategy enum values."""
        assert RetryStrategy.IMMEDIATE.value == "immediate"
        assert RetryStrategy.EXPONENTIAL_BACKOFF.value == "exponential_backoff"
        assert RetryStrategy.LINEAR_BACKOFF.value == "linear_backoff"
        assert RetryStrategy.CUSTOM.value == "custom"

    def test_error_details_creation(self) -> None:
        """Test creating error details."""
        error_details = ErrorDetails(
            error_type=ErrorType.PROCESSING_ERROR,
            error_code="PROC_001",
            error_message="Processing failed",
            error_context={"step": "data_analysis"},
        )

        assert error_details.error_type == ErrorType.PROCESSING_ERROR
        assert error_details.error_code == "PROC_001"
        assert error_details.error_message == "Processing failed"
        assert error_details.retry_count == 0
        assert error_details.max_retries == 3

    def test_error_details_can_retry(self) -> None:
        """Test retry capability logic."""
        # Retryable error
        retryable_error = ErrorDetails(
            error_type=ErrorType.PROCESSING_ERROR,
            error_code="PROC_001",
            error_message="Processing failed",
            error_context={},
        )
        assert retryable_error.can_retry() is True

        # Non-retryable error
        non_retryable_error = ErrorDetails(
            error_type=ErrorType.VALIDATION_ERROR,
            error_code="VAL_001",
            error_message="Invalid format",
            error_context={},
        )
        assert non_retryable_error.can_retry() is False

        # Max retries exceeded
        max_retries_error = ErrorDetails(
            error_type=ErrorType.PROCESSING_ERROR,
            error_code="PROC_001",
            error_message="Processing failed",
            error_context={},
            retry_count=3,
        )
        assert max_retries_error.can_retry() is False

    def test_error_details_should_retry_now(self) -> None:
        """Test retry timing logic."""
        error_details = ErrorDetails(
            error_type=ErrorType.PROCESSING_ERROR,
            error_code="PROC_001",
            error_message="Processing failed",
            error_context={},
        )

        # Should retry immediately if no retry_after set
        assert error_details.should_retry_now() is True

        # Should not retry if retry_after is in the future
        future_time = datetime.now(timezone.utc) + timedelta(seconds=10)
        error_details.retry_after = future_time
        assert error_details.should_retry_now() is False

        # Should retry if retry_after is in the past
        past_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        error_details.retry_after = past_time
        assert error_details.should_retry_now() is True

    def test_retry_handler_calculate_delay(self) -> None:
        """Test retry delay calculations."""
        handler = RetryHandler(max_retries=3, base_delay=1.0)

        # Immediate retry
        delay = handler.calculate_retry_delay(0, RetryStrategy.IMMEDIATE)
        assert delay == 0.0

        # Exponential backoff
        delay = handler.calculate_retry_delay(1, RetryStrategy.EXPONENTIAL_BACKOFF)
        assert delay == 2.0  # 1 * 2^1

        delay = handler.calculate_retry_delay(2, RetryStrategy.EXPONENTIAL_BACKOFF)
        assert delay == 4.0  # 1 * 2^2

        # Linear backoff
        delay = handler.calculate_retry_delay(1, RetryStrategy.LINEAR_BACKOFF)
        assert delay == 2.0  # 1 * (1 + 1)

        delay = handler.calculate_retry_delay(2, RetryStrategy.LINEAR_BACKOFF)
        assert delay == 3.0  # 1 * (2 + 1)

    def test_retry_handler_prepare_for_retry(self) -> None:
        """Test preparing error details for retry."""
        handler = RetryHandler(max_retries=3, base_delay=1.0)

        error_details = ErrorDetails(
            error_type=ErrorType.PROCESSING_ERROR,
            error_code="PROC_001",
            error_message="Processing failed",
            error_context={},
        )

        # Prepare for exponential backoff retry
        retry_details = handler.prepare_for_retry(
            error_details, RetryStrategy.EXPONENTIAL_BACKOFF
        )

        assert retry_details.retry_count == 1
        assert retry_details.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert retry_details.retry_after is not None

        # Verify retry_after is in the future
        assert retry_details.retry_after > datetime.now(timezone.utc)

    def test_create_error_response(self) -> None:
        """Test creating error response data."""
        error_data = create_error_response(
            error_type=ErrorType.PROCESSING_ERROR,
            error_code="PROC_001",
            error_message="Processing failed",
            error_context={"step": "data_analysis"},
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            source="test_system",
        )

        assert error_data["error_type"] == "processing_error"
        assert error_data["error_code"] == "PROC_001"
        assert error_data["error_message"] == "Processing failed"
        assert error_data["error_context"]["step"] == "data_analysis"
        assert error_data["retry_strategy"] == "exponential_backoff"
        assert error_data["retry_count"] == 0
        assert error_data["max_retries"] == 3
        assert error_data["source"] == "test_system"

    def test_is_retryable_error(self) -> None:
        """Test retryable error type checking."""
        assert is_retryable_error(ErrorType.PROCESSING_ERROR) is True
        assert is_retryable_error(ErrorType.TIMEOUT_ERROR) is True
        assert is_retryable_error(ErrorType.RESOURCE_ERROR) is True
        assert is_retryable_error(ErrorType.NETWORK_ERROR) is True

        assert is_retryable_error(ErrorType.VALIDATION_ERROR) is False
        assert is_retryable_error(ErrorType.UNKNOWN_ERROR) is False

    def test_create_system_error(self) -> None:
        """Test creating system errors."""
        error_details = create_system_error(
            error_type=ErrorType.CONFIGURATION_ERROR,
            error_code="CONFIG_001",
            error_message="Invalid configuration",
            error_context={"file": "config.yaml"},
            source="config_manager",
        )

        assert error_details.error_type == ErrorType.CONFIGURATION_ERROR
        assert error_details.error_code == "CONFIG_001"
        assert error_details.error_message == "Invalid configuration"
        assert error_details.source == "config_manager"
        assert error_details.retry_count == 0
        assert error_details.max_retries == 3

    def test_create_error_event(self) -> None:
        """Test creating error event messages."""
        error_message = create_error_event(
            original_message_id="msg_123",
            error_type=ErrorType.PROCESSING_ERROR.value,
            error_code="PROC_001",
            error_message="Processing failed",
            error_context={"step": "data_analysis"},
        )

        assert error_message.header.message_type.value == "event"
        assert error_message.body.action == "error_occurred"
        assert error_message.body.status == MessageStatus.FAILED

        error_data = error_message.body.data
        assert error_data["original_message_id"] == "msg_123"
        assert error_data["error_type"] == "processing_error"
        assert error_data["error_code"] == "PROC_001"
        assert error_data["error_message"] == "Processing failed"

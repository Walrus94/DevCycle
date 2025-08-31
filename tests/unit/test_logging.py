"""Tests for the logging system."""

import json
import logging
from typing import Any

import pytest

from devcycle.core.logging import get_logger, log_agent_activity, log_workflow_step


@pytest.mark.unit
class TestLogging:
    """Test logging functionality."""

    def test_get_logger(self) -> None:
        """Test that get_logger returns a structlog logger."""
        logger = get_logger("test_module")
        # structlog.get_logger returns a BoundLoggerLazyProxy initially
        assert hasattr(logger, "info")  # Check it has logger methods
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")
        # Test that we can actually log something
        logger.info("test message")

    def test_agent_activity_logging(self, caplog: Any) -> None:
        """Test agent activity logging."""
        with caplog.at_level(logging.INFO):
            log_agent_activity(
                "test_agent", "test_action", "started", {"detail": "test"}
            )

        # Check that log was created
        assert len(caplog.records) == 1
        record = caplog.records[0]

        # Parse JSON log
        log_data = json.loads(record.getMessage())

        # Verify structure
        assert log_data["agent"] == "test_agent"
        assert log_data["action"] == "test_action"
        assert log_data["status"] == "started"
        assert log_data["detail"] == "test"
        assert log_data["event_type"] == "agent_activity"

    def test_workflow_step_logging(self, caplog: Any) -> None:
        """Test workflow step logging."""
        with caplog.at_level(logging.INFO):
            log_workflow_step(
                "test_workflow", "test_step", 1, 3, "started", {"detail": "test"}
            )

        # Check that log was created
        assert len(caplog.records) == 1
        record = caplog.records[0]

        # Parse JSON log
        log_data = json.loads(record.getMessage())

        # Verify structure
        assert log_data["workflow_id"] == "test_workflow"
        assert log_data["step"] == "test_step"
        assert log_data["step_number"] == 1
        assert log_data["total_steps"] == 3
        assert log_data["progress"] == "1/3"
        assert log_data["status"] == "started"
        assert log_data["detail"] == "test"
        assert log_data["event_type"] == "workflow_step"

    def test_json_output_format(self, caplog: Any) -> None:
        """Test that logs are output in JSON format."""
        with caplog.at_level(logging.INFO):
            logger = get_logger("test_json")
            logger.info("test message", key="value", number=42)

        # Check that log was created
        assert len(caplog.records) == 1
        record = caplog.records[0]

        # Verify it's valid JSON
        log_data = json.loads(record.getMessage())
        assert log_data["key"] == "value"
        assert log_data["number"] == 42
        assert "event" in log_data  # structlog adds this

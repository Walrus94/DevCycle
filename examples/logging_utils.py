#!/usr/bin/env python3
"""
Logging utilities for DevCycle examples.

This module provides a simple logging setup for examples that can be used
instead of print statements, while maintaining readability for demo purposes.
"""

import logging
import sys
from typing import Any, Optional

from devcycle.core.logging import get_logger, setup_logging


class ExampleLogger:
    """
    Logger for examples that provides both structured logging and console output.

    This logger is designed for examples and demos, providing both structured
    logging for production compatibility and readable console output for demos.
    """

    def __init__(self, name: str, enable_console: bool = True):
        """Initialize the example logger."""
        self.name = name
        self.enable_console = enable_console
        self.structured_logger = get_logger(name)

        # Setup console logging for examples
        if enable_console:
            self.console_logger = logging.getLogger(f"{name}.console")
            self.console_logger.setLevel(logging.INFO)

            # Remove existing handlers
            for handler in self.console_logger.handlers[:]:
                self.console_logger.removeHandler(handler)

            # Add console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)

            # Simple format for console
            formatter = logging.Formatter("%(message)s")
            console_handler.setFormatter(formatter)

            self.console_logger.addHandler(console_handler)
            self.console_logger.propagate = False

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message to both structured logger and console."""
        self.structured_logger.info(message, **kwargs)
        if self.enable_console:
            self.console_logger.info(message)

    def success(self, message: str, **kwargs: Any) -> None:
        """Log success message."""
        self.structured_logger.info(message, event_type="success", **kwargs)
        if self.enable_console:
            self.console_logger.info(f"✅ {message}")

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self.structured_logger.error(message, **kwargs)
        if self.enable_console:
            self.console_logger.error(f"❌ {message}")

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self.structured_logger.warning(message, **kwargs)
        if self.enable_console:
            self.console_logger.warning(f"⚠️  {message}")

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self.structured_logger.debug(message, **kwargs)
        if self.enable_console:
            self.console_logger.debug(f"🔍 {message}")

    def step(
        self, step_name: str, step_number: Optional[int] = None, **kwargs: Any
    ) -> None:
        """Log a demo step."""
        if step_number:
            message = f"Step {step_number}: {step_name}"
        else:
            message = f"Step: {step_name}"

        self.structured_logger.info(message, event_type="demo_step", **kwargs)
        if self.enable_console:
            self.console_logger.info(f"\n📋 {message}")

    def section(self, title: str, **kwargs: Any) -> None:
        """Log a section header."""
        self.structured_logger.info(title, event_type="demo_section", **kwargs)
        if self.enable_console:
            self.console_logger.info(f"\n🚀 {title}")
            self.console_logger.info("=" * 50)

    def data(self, data: Any, title: str = "Data", **kwargs: Any) -> None:
        """Log structured data."""
        import json

        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, indent=2)
        else:
            data_str = str(data)

        self.structured_logger.info(
            title, data=data_str, event_type="demo_data", **kwargs
        )

        if self.enable_console:
            self.console_logger.info(f"\n📊 {title}:")
            self.console_logger.info(data_str)

    def demo_start(self, demo_name: str, **kwargs: Any) -> None:
        """Log demo start."""
        self.structured_logger.info(
            f"Demo started: {demo_name}",
            demo_name=demo_name,
            event_type="demo_start",
            **kwargs,
        )
        if self.enable_console:
            self.console_logger.info(f"🚀 {demo_name}")
            self.console_logger.info("=" * 50)

    def demo_end(self, demo_name: str, success: bool = True, **kwargs: Any) -> None:
        """Log demo end."""
        status = "completed successfully" if success else "failed"
        self.structured_logger.info(
            f"Demo {status}: {demo_name}",
            demo_name=demo_name,
            success=success,
            event_type="demo_end",
            **kwargs,
        )
        if self.enable_console:
            if success:
                self.console_logger.info(f"\n✅ {demo_name} completed successfully!")
            else:
                self.console_logger.error(f"\n❌ {demo_name} failed!")


def get_example_logger(name: str, enable_console: bool = True) -> ExampleLogger:
    """
    Get an example logger instance.

    Args:
        name: Logger name (usually __name__)
        enable_console: Whether to enable console output for demos

    Returns:
        ExampleLogger instance
    """
    return ExampleLogger(name, enable_console)


def setup_example_logging(level: str = "INFO", enable_console: bool = True) -> None:
    """
    Set up logging for examples.

    Args:
        level: Logging level
        enable_console: Whether to enable console output
    """
    # Setup structured logging
    setup_logging(level=level, json_output=True)

    if enable_console:
        # Setup console logging for examples
        console_logger = logging.getLogger("examples.console")
        console_logger.setLevel(getattr(logging, level.upper()))

        # Remove existing handlers
        for handler in console_logger.handlers[:]:
            console_logger.removeHandler(handler)

        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))

        # Simple format for console
        formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(formatter)

        console_logger.addHandler(console_handler)
        console_logger.propagate = False

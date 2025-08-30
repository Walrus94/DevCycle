"""
DevCycle - AI-Powered Application Development Lifecycle Automation System

A Proof of Concept (POC) that leverages multiple specialized AI agents to streamline
software development processes through Hugging Face Spaces integration.
"""

__version__ = "0.1.0"
__author__ = "DevCycle Team"
__email__ = "team@devcycle.dev"
__description__ = "AI-Powered Application Development Lifecycle Automation System"

# Core imports
from .core.config import DevCycleConfig
from .core.logging import setup_logging

# Initialize logging
setup_logging()

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "DevCycleConfig",
    "setup_logging",
]

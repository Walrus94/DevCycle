"""
Service layer for DevCycle.

This package contains business logic services that abstract
complex operations and coordinate between repositories and external services.
"""

from .agent_availability_service import AgentAvailabilityService
from .agent_service import AgentService
from .base import BaseService

# UserService removed - using FastAPI Users directly

__all__ = [
    "BaseService",
    "AgentService",
    "AgentAvailabilityService",
]

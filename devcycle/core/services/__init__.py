"""
Service layer for DevCycle.

This package contains business logic services that abstract
complex operations and coordinate between repositories and external services.
"""

from .agent_availability_service import AgentAvailabilityService
from .agent_service import AgentService

# UserService removed - using FastAPI Users directly
# BaseService removed - was unnecessary abstraction

__all__ = [
    "AgentService",
    "AgentAvailabilityService",
]

"""
Repository layer for DevCycle.

This module provides data access abstractions using the repository pattern
to separate business logic from data access concerns.
"""

from .agent_repository import AgentRepository, AgentTaskRepository
from .base import BaseRepository

# UserRepository removed - using FastAPI Users SQLAlchemyUserDatabase directly

__all__ = [
    "BaseRepository",
    "AgentRepository",
    "AgentTaskRepository",
]

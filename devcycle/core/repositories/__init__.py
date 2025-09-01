"""
Repository layer for DevCycle.

This module provides data access abstractions using the repository pattern
to separate business logic from data access concerns.
"""

from .base import BaseRepository
from .factory import RepositoryFactory, get_repository_factory
from .user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "RepositoryFactory",
    "get_repository_factory",
]

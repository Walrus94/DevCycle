"""
Repository factory for DevCycle.

This module provides a factory for creating repository instances
and managing their lifecycle for dependency injection.
"""

from typing import Any, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from .user_repository import UserRepository

# Generic type for repositories
R = TypeVar("R", bound=BaseRepository)


class RepositoryFactory:
    """
    Factory for creating repository instances.

    This factory manages the creation and lifecycle of repository
    instances, providing a clean interface for dependency injection.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository factory with database session.

        Args:
            session: Async database session
        """
        self.session = session

    def get_user_repository(self) -> UserRepository:
        """
        Get user repository instance.

        Returns:
            UserRepository instance
        """
        return UserRepository(self.session)

    def get_repository(self, repository_class: Type[R]) -> R:
        """
        Get repository instance by class.

        Args:
            repository_class: Repository class to instantiate

        Returns:
            Repository instance

        Raises:
            ValueError: If repository class is not supported
        """
        if repository_class == UserRepository:
            return UserRepository(self.session)  # type: ignore[return-value]

        raise ValueError(f"Unsupported repository class: {repository_class}")

    def create_repository(
        self, repository_class: Type[R], *args: Any, **kwargs: Any
    ) -> R:
        """
        Create custom repository instance.

        Args:
            repository_class: Repository class to instantiate
            *args: Positional arguments for repository constructor
            **kwargs: Keyword arguments for repository constructor

        Returns:
            Repository instance
        """
        return repository_class(self.session, *args, **kwargs)


# Dependency function for FastAPI
def get_repository_factory(session: AsyncSession) -> RepositoryFactory:
    """
    Get repository factory instance for dependency injection.

    Args:
        session: Async database session

    Returns:
        RepositoryFactory instance
    """
    return RepositoryFactory(session)

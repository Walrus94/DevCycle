"""
Base service interface for DevCycle.

This module defines the base service class that provides common
service operations and patterns for all business logic services.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from ..repositories.base import BaseRepository

T = TypeVar("T")


class BaseService(Generic[T], ABC):
    """
    Base service class providing common service operations.

    This abstract base class defines the interface for all services
    and provides common functionality for entity management.
    """

    def __init__(self, repository: BaseRepository[T]):
        """
        Initialize service with repository.

        Args:
            repository: Repository instance for data access
        """
        self.repository = repository

    async def create(self, **kwargs: Any) -> T:
        """
        Create a new entity.

        Args:
            **kwargs: Entity attributes

        Returns:
            Created entity instance
        """
        return await self.repository.create(**kwargs)

    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity instance or None if not found
        """
        return await self.repository.get_by_id(entity_id)

    async def get_all(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[T]:
        """
        Get all entities with optional pagination.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entity instances
        """
        return await self.repository.get_all(limit=limit, offset=offset)

    async def update(self, entity_id: UUID, **kwargs: Any) -> Optional[T]:
        """
        Update entity by ID.

        Args:
            entity_id: Entity identifier
            **kwargs: Attributes to update

        Returns:
            Updated entity instance or None if not found
        """
        return await self.repository.update(entity_id, **kwargs)

    async def delete(self, entity_id: UUID) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete(entity_id)

    async def exists(self, entity_id: UUID) -> bool:
        """
        Check if entity exists.

        Args:
            entity_id: Entity identifier

        Returns:
            True if entity exists, False otherwise
        """
        return await self.repository.exists(entity_id)

    async def count(self) -> int:
        """
        Count total entities.

        Returns:
            Total number of entities
        """
        return await self.repository.count()

    async def find_by(self, **filters: Any) -> List[T]:
        """
        Find entities by filters.

        Args:
            **filters: Filter criteria

        Returns:
            List of matching entity instances
        """
        return await self.repository.find_by(**filters)

    async def find_one_by(self, **filters: Any) -> Optional[T]:
        """
        Find single entity by filters.

        Args:
            **filters: Filter criteria

        Returns:
            Entity instance or None if not found
        """
        return await self.repository.find_one_by(**filters)

    @abstractmethod
    async def validate_business_rules(self, entity: T, **kwargs: Any) -> bool:
        """
        Validate business rules for entity operations.

        Args:
            entity: Entity instance to validate
            **kwargs: Additional validation context

        Returns:
            True if validation passes, False otherwise

        Raises:
            ValidationError: If business rules are violated
        """
        pass

    @abstractmethod
    async def apply_business_logic(self, entity: T, **kwargs: Any) -> T:
        """
        Apply business logic to entity.

        Args:
            entity: Entity instance to process
            **kwargs: Additional business logic context

        Returns:
            Processed entity instance
        """
        pass

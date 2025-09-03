"""
Base repository interface for DevCycle.

This module provides the base repository pattern implementation
that all data access repositories should extend.
"""

from abc import ABC
from typing import Any, List, Optional, Union
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.models import Base


class BaseRepository(ABC):
    """
    Base repository interface providing common CRUD operations.

    This abstract base class defines the contract that all repositories
    must implement, providing a consistent interface for data access.
    """

    def __init__(self, session: AsyncSession, model: type[Base]):
        """
        Initialize repository with database session and model.

        Args:
            session: Async database session
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model

    async def create(self, **kwargs: Any) -> Base:
        """
        Create a new entity.

        Args:
            **kwargs: Entity attributes

        Returns:
            Created entity instance
        """
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def get_by_id(self, entity_id: Union[int, UUID]) -> Optional[Base]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity instance or None if not found
        """
        stmt = select(self.model).where(self.model.id == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Base]:
        """
        Get all entities with optional pagination.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities
        """
        stmt = select(self.model)

        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(
        self, entity_id: Union[int, UUID], **kwargs: Any
    ) -> Optional[Base]:
        """
        Update entity by ID.

        Args:
            entity_id: Entity identifier
            **kwargs: Fields to update

        Returns:
            Updated entity instance or None if not found
        """
        stmt = (
            update(self.model)
            .where(self.model.id == entity_id)
            .values(**kwargs)
            .returning(self.model)
        )

        await self.session.execute(stmt)
        await self.session.commit()

        # Refresh the entity to get updated values
        entity = await self.get_by_id(entity_id)
        return entity

    async def delete(self, entity_id: Union[int, UUID]) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(self.model).where(self.model.id == entity_id)
        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount > 0

    async def exists(self, entity_id: Union[int, UUID]) -> bool:
        """
        Check if entity exists by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            True if exists, False otherwise
        """
        stmt = select(self.model.id).where(self.model.id == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        """
        Get total count of entities.

        Returns:
            Total number of entities
        """
        stmt = select(self.model.id)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def find_by(self, **filters: Any) -> List[Base]:
        """
        Find entities by filters.

        Args:
            **filters: Field-value pairs to filter by

        Returns:
            List of matching entities
        """
        stmt = select(self.model)

        for field, value in filters.items():
            if hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_one_by(self, **filters: Any) -> Optional[Base]:
        """
        Find single entity by filters.

        Args:
            **filters: Field-value pairs to filter by

        Returns:
            Matching entity or None if not found
        """
        stmt = select(self.model)

        for field, value in filters.items():
            if hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def with_relationships(self, *relationships: str) -> "BaseRepository":
        """
        Add relationship loading to the next query.

        Args:
            *relationships: Relationship names to load

        Returns:
            Self for method chaining
        """
        self._relationships = relationships
        return self

    async def _load_relationships(self, stmt: Any) -> Any:
        """Load relationships if specified."""
        if hasattr(self, "_relationships"):
            for relationship in self._relationships:
                if hasattr(self.model, relationship):
                    stmt = stmt.options(selectinload(getattr(self.model, relationship)))
            delattr(self, "_relationships")
        return stmt

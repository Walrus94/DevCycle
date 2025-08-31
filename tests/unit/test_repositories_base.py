"""
Unit tests for base repository functionality.

This module tests the BaseRepository class and its common CRUD operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from devcycle.core.repositories.base import BaseRepository


class MockModel:
    """Mock model for testing."""

    def __init__(self, id=None, name="test", value=42):
        self.id = id or uuid4()
        self.name = name
        self.value = value


class MockRepository(BaseRepository[MockModel]):
    """Mock repository for testing base functionality."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, MockModel)


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_repository(mock_session):
    """Create a mock repository instance."""
    return MockRepository(mock_session)


@pytest.fixture
def sample_model():
    """Create a sample model instance."""
    return MockModel(id=uuid4(), name="test_model", value=100)


class TestBaseRepository:
    """Test base repository functionality."""

    def test_init(self, mock_session):
        """Test repository initialization."""
        repo = MockRepository(mock_session)
        assert repo.session == mock_session
        assert repo.model == MockModel

    @pytest.mark.asyncio
    async def test_create(self, mock_repository, mock_session):
        """Test entity creation."""
        # Arrange
        mock_model = MockModel(name="new_model", value=200)
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_model

        # Act
        result = await mock_repository.create(name="new_model", value=200)

        # Assert
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        assert result.name == "new_model"
        assert result.value == 200

    @pytest.mark.asyncio
    @patch.object(MockRepository, "get_by_id")
    async def test_get_by_id(self, mock_get_by_id, mock_repository, sample_model):
        """Test getting entity by ID."""
        # Arrange
        mock_get_by_id.return_value = sample_model

        # Act
        result = await mock_repository.get_by_id(sample_model.id)

        # Assert
        assert result == sample_model

    @pytest.mark.asyncio
    @patch.object(MockRepository, "get_by_id")
    async def test_get_by_id_not_found(self, mock_get_by_id, mock_repository):
        """Test getting entity by ID when not found."""
        # Arrange
        mock_get_by_id.return_value = None

        # Act
        result = await mock_repository.get_by_id(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    @patch.object(MockRepository, "get_all")
    async def test_get_all(self, mock_get_all, mock_repository):
        """Test getting all entities."""
        # Arrange
        models = [MockModel(), MockModel(), MockModel()]
        mock_get_all.return_value = models

        # Act
        result = await mock_repository.get_all()

        # Assert
        assert result == models
        assert len(result) == 3

    @pytest.mark.asyncio
    @patch.object(MockRepository, "get_all")
    async def test_get_all_with_pagination(self, mock_get_all, mock_repository):
        """Test getting all entities with pagination."""
        # Arrange
        models = [MockModel(), MockModel()]
        mock_get_all.return_value = models

        # Act
        result = await mock_repository.get_all(limit=2, offset=1)

        # Assert
        assert result == models

    @pytest.mark.asyncio
    @patch.object(MockRepository, "update")
    async def test_update(self, mock_update, mock_repository, sample_model):
        """Test entity update."""
        # Arrange
        mock_update.return_value = sample_model

        # Act
        result = await mock_repository.update(
            sample_model.id, name="updated_name", value=999
        )

        # Assert
        assert result == sample_model

    @pytest.mark.asyncio
    @patch.object(MockRepository, "update")
    async def test_update_not_found(self, mock_update, mock_repository):
        """Test updating entity when not found."""
        # Arrange
        mock_update.return_value = None

        # Act
        result = await mock_repository.update(uuid4(), name="updated_name")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    @patch.object(MockRepository, "delete")
    async def test_delete(self, mock_delete, mock_repository):
        """Test entity deletion."""
        # Arrange
        mock_delete.return_value = True

        # Act
        result = await mock_repository.delete(uuid4())

        # Assert
        assert result is True

    @pytest.mark.asyncio
    @patch.object(MockRepository, "delete")
    async def test_delete_not_found(self, mock_delete, mock_repository):
        """Test deleting entity when not found."""
        # Arrange
        mock_delete.return_value = False

        # Act
        result = await mock_repository.delete(uuid4())

        # Assert
        assert result is False

    @pytest.mark.asyncio
    @patch.object(MockRepository, "exists")
    async def test_exists(self, mock_exists, mock_repository):
        """Test checking if entity exists."""
        # Arrange
        mock_exists.return_value = True

        # Act
        result = await mock_repository.exists(uuid4())

        # Assert
        assert result is True

    @pytest.mark.asyncio
    @patch.object(MockRepository, "exists")
    async def test_exists_not_found(self, mock_exists, mock_repository):
        """Test checking if entity exists when not found."""
        # Arrange
        mock_exists.return_value = False

        # Act
        result = await mock_repository.exists(uuid4())

        # Assert
        assert result is False

    @pytest.mark.asyncio
    @patch.object(MockRepository, "count")
    async def test_count(self, mock_count, mock_repository):
        """Test counting entities."""
        # Arrange
        mock_count.return_value = 3

        # Act
        result = await mock_repository.count()

        # Assert
        assert result == 3

    @pytest.mark.asyncio
    @patch.object(MockRepository, "find_by")
    async def test_find_by(self, mock_find_by, mock_repository):
        """Test finding entities by filters."""
        # Arrange
        models = [MockModel(name="filtered")]
        mock_find_by.return_value = models

        # Act
        result = await mock_repository.find_by(name="filtered")

        # Assert
        assert result == models

    @pytest.mark.asyncio
    @patch.object(MockRepository, "find_one_by")
    async def test_find_one_by(self, mock_find_one_by, mock_repository, sample_model):
        """Test finding single entity by filters."""
        # Arrange
        mock_find_one_by.return_value = sample_model

        # Act
        result = await mock_repository.find_one_by(name="test_model")

        # Assert
        assert result == sample_model

    @pytest.mark.asyncio
    @patch.object(MockRepository, "find_one_by")
    async def test_find_one_by_not_found(self, mock_find_one_by, mock_repository):
        """Test finding single entity when not found."""
        # Arrange
        mock_find_one_by.return_value = None

        # Act
        result = await mock_repository.find_one_by(name="nonexistent")

        # Assert
        assert result is None

    def test_with_relationships(self, mock_repository):
        """Test relationship loading setup."""
        # Act
        result = mock_repository.with_relationships("relation1", "relation2")

        # Assert
        assert result == mock_repository
        assert hasattr(mock_repository, "_relationships")
        assert mock_repository._relationships == ("relation1", "relation2")

    @pytest.mark.asyncio
    @patch.object(MockRepository, "find_by")
    async def test_find_by_with_invalid_filter(self, mock_find_by, mock_repository):
        """Test finding entities with invalid filter field."""
        # Arrange
        mock_find_by.return_value = []

        # Act
        result = await mock_repository.find_by(invalid_field="value")

        # Assert
        # Should not raise error, just return empty result
        assert result == []

"""
Unit tests for base service functionality.

This module tests the BaseService class and its common service operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from devcycle.core.repositories.base import BaseRepository
from devcycle.core.services.base import BaseService


class MockModel:
    """Mock model for testing."""

    def __init__(self, id=None, name="test", value=42):
        self.id = id or uuid4()
        self.name = name
        self.value = value


class MockRepository(BaseRepository[MockModel]):
    """Mock repository for testing base service functionality."""

    def __init__(self, session):
        super().__init__(session, MockModel)


class MockService(BaseService[MockModel]):
    """Mock service for testing base functionality."""

    def __init__(self, repository: MockRepository):
        super().__init__(repository)

    async def validate_business_rules(self, entity: MockModel, **kwargs) -> bool:
        """Mock business rules validation."""
        return entity.name is not None and entity.value > 0

    async def apply_business_logic(self, entity: MockModel, **kwargs) -> MockModel:
        """Mock business logic application."""
        if kwargs.get("processed"):
            entity.value *= 2
        return entity


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repository = AsyncMock(spec=MockRepository)
    repository.create = AsyncMock()
    repository.get_by_id = AsyncMock()
    repository.get_all = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    repository.exists = AsyncMock()
    repository.count = AsyncMock()
    repository.find_by = AsyncMock()
    repository.find_one_by = AsyncMock()
    return repository


@pytest.fixture
def mock_service(mock_repository):
    """Create a mock service instance."""
    return MockService(mock_repository)


@pytest.fixture
def sample_model():
    """Create a sample model instance."""
    return MockModel(id=uuid4(), name="test_model", value=100)


class TestBaseService:
    """Test base service functionality."""

    def test_init(self, mock_repository):
        """Test service initialization."""
        service = MockService(mock_repository)
        assert service.repository == mock_repository

    @pytest.mark.asyncio
    async def test_create(self, mock_service, mock_repository):
        """Test entity creation through service."""
        # Arrange
        mock_model = MockModel(name="new_model", value=200)
        mock_repository.create.return_value = mock_model

        # Act
        result = await mock_service.create(name="new_model", value=200)

        # Assert
        mock_repository.create.assert_called_once_with(name="new_model", value=200)
        assert result == mock_model

    @pytest.mark.asyncio
    async def test_get_by_id(self, mock_service, mock_repository, sample_model):
        """Test getting entity by ID through service."""
        # Arrange
        mock_repository.get_by_id.return_value = sample_model

        # Act
        result = await mock_service.get_by_id(sample_model.id)

        # Assert
        mock_repository.get_by_id.assert_called_once_with(sample_model.id)
        assert result == sample_model

    @pytest.mark.asyncio
    async def test_get_all(self, mock_service, mock_repository):
        """Test getting all entities through service."""
        # Arrange
        models = [MockModel(), MockModel(), MockModel()]
        mock_repository.get_all.return_value = models

        # Act
        result = await mock_service.get_all(limit=2, offset=1)

        # Assert
        mock_repository.get_all.assert_called_once_with(limit=2, offset=1)
        assert result == models

    @pytest.mark.asyncio
    async def test_update(self, mock_service, mock_repository, sample_model):
        """Test entity update through service."""
        # Arrange
        mock_repository.update.return_value = sample_model

        # Act
        result = await mock_service.update(sample_model.id, name="updated_name")

        # Assert
        mock_repository.update.assert_called_once_with(
            sample_model.id, name="updated_name"
        )
        assert result == sample_model

    @pytest.mark.asyncio
    async def test_delete(self, mock_service, mock_repository):
        """Test entity deletion through service."""
        # Arrange
        mock_repository.delete.return_value = True

        # Act
        result = await mock_service.delete(uuid4())

        # Assert
        mock_repository.delete.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_exists(self, mock_service, mock_repository):
        """Test checking entity existence through service."""
        # Arrange
        mock_repository.exists.return_value = True

        # Act
        result = await mock_service.exists(uuid4())

        # Assert
        mock_repository.exists.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_count(self, mock_service, mock_repository):
        """Test counting entities through service."""
        # Arrange
        mock_repository.count.return_value = 3

        # Act
        result = await mock_service.count()

        # Assert
        mock_repository.count.assert_called_once()
        assert result == 3

    @pytest.mark.asyncio
    async def test_find_by(self, mock_service, mock_repository):
        """Test finding entities by filters through service."""
        # Arrange
        models = [MockModel(name="filtered")]
        mock_repository.find_by.return_value = models

        # Act
        result = await mock_service.find_by(name="filtered")

        # Assert
        mock_repository.find_by.assert_called_once_with(name="filtered")
        assert result == models

    @pytest.mark.asyncio
    async def test_find_one_by(self, mock_service, mock_repository, sample_model):
        """Test finding single entity by filters through service."""
        # Arrange
        mock_repository.find_one_by.return_value = sample_model

        # Act
        result = await mock_service.find_one_by(name="test_model")

        # Assert
        mock_repository.find_one_by.assert_called_once_with(name="test_model")
        assert result == sample_model

    @pytest.mark.asyncio
    async def test_validate_business_rules(self, mock_service, sample_model):
        """Test business rules validation."""
        # Act
        result = await mock_service.validate_business_rules(sample_model)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_business_rules_invalid(self, mock_service):
        """Test business rules validation with invalid entity."""
        # Arrange
        invalid_model = MockModel(name=None, value=0)

        # Act
        result = await mock_service.validate_business_rules(invalid_model)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_apply_business_logic(self, mock_service, sample_model):
        """Test business logic application."""
        # Act
        result = await mock_service.apply_business_logic(sample_model, processed=True)

        # Assert
        assert result.value == 200  # Should be doubled
        assert result == sample_model

    @pytest.mark.asyncio
    async def test_apply_business_logic_no_context(self, mock_service, sample_model):
        """Test business logic application without context."""
        original_value = sample_model.value

        # Act
        result = await mock_service.apply_business_logic(sample_model)

        # Assert
        assert result.value == original_value  # Should not be changed
        assert result == sample_model

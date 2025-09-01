"""
Unit tests for repository factory functionality.

This module tests the RepositoryFactory class and its repository creation methods.
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from devcycle.core.repositories.factory import RepositoryFactory, get_repository_factory
from devcycle.core.repositories.user_repository import UserRepository


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def repository_factory(mock_session):
    """Create a repository factory instance."""
    return RepositoryFactory(mock_session)


class TestRepositoryFactory:
    """Test repository factory functionality."""

    def test_init(self, mock_session):
        """Test factory initialization."""
        factory = RepositoryFactory(mock_session)
        assert factory.session == mock_session

    def test_get_user_repository(self, repository_factory):
        """Test getting user repository instance."""
        # Act
        user_repo = repository_factory.get_user_repository()

        # Assert
        assert isinstance(user_repo, UserRepository)
        assert user_repo.session == repository_factory.session
        assert user_repo.model.__name__ == "User"

    def test_get_repository_by_class(self, repository_factory):
        """Test getting repository by class."""
        # Act
        user_repo = repository_factory.get_repository(UserRepository)

        # Assert
        assert isinstance(user_repo, UserRepository)
        assert user_repo.session == repository_factory.session

    def test_get_repository_unsupported_class(self, repository_factory):
        """Test getting repository with unsupported class."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported repository class"):
            repository_factory.get_repository(str)

    def test_create_repository(self, repository_factory):
        """Test creating a repository instance."""
        # Act
        user_repo = repository_factory.create_repository(UserRepository)

        # Assert
        assert isinstance(user_repo, UserRepository)
        assert user_repo.session == repository_factory.session

    def test_multiple_repositories_same_session(self, repository_factory):
        """Test creating multiple repositories with the same session."""
        # Act
        user_repo1 = repository_factory.create_repository(UserRepository)
        user_repo2 = repository_factory.create_repository(UserRepository)

        # Assert
        assert user_repo1.session == user_repo2.session
        assert user_repo1.session == repository_factory.session

    def test_repository_independence(self, repository_factory):
        """Test that repositories are independent instances."""
        # Act
        user_repo1 = repository_factory.get_user_repository()
        user_repo2 = repository_factory.get_user_repository()

        # Assert
        assert user_repo1 is not user_repo2  # Different instances
        assert user_repo1.session == user_repo2.session  # Same session


class TestGetRepositoryFactory:
    """Test get_repository_factory dependency function."""

    def test_get_repository_factory(self, mock_session):
        """Test getting repository factory from dependency function."""
        # Act
        factory = get_repository_factory(mock_session)

        # Assert
        assert isinstance(factory, RepositoryFactory)
        assert factory.session == mock_session

    def test_get_repository_factory_session_preservation(self, mock_session):
        """Test that factory preserves the session reference."""
        # Act
        factory = get_repository_factory(mock_session)

        # Assert
        assert factory.session is mock_session

    def test_get_repository_factory_creates_new_instance(self, mock_session):
        """Test that dependency function creates new factory instances."""
        # Act
        factory1 = get_repository_factory(mock_session)
        factory2 = get_repository_factory(mock_session)

        # Assert
        assert factory1 is not factory2  # Different instances
        assert factory1.session == factory2.session  # Same session


class TestRepositoryFactoryIntegration:
    """Test repository factory integration with actual repositories."""

    def test_user_repository_through_factory(self, repository_factory):
        """Test that user repository works correctly through factory."""
        # Arrange
        user_repo = repository_factory.get_user_repository()

        # Act & Assert
        assert user_repo.session == repository_factory.session
        assert user_repo.model.__name__ == "User"

        # Test that repository methods are callable
        assert hasattr(user_repo, "get_by_email")
        assert hasattr(user_repo, "get_active_users")
        assert hasattr(user_repo, "update_user_status")

    def test_repository_methods_accessible(self, repository_factory):
        """Test that repository methods are accessible through factory."""
        # Arrange
        user_repo = repository_factory.get_user_repository()

        # Act & Assert
        # These should not raise AttributeError
        assert callable(user_repo.get_by_email)
        assert callable(user_repo.get_active_users)
        assert callable(user_repo.get_verified_users)
        assert callable(user_repo.get_superusers)
        assert callable(user_repo.count_active_users)
        assert callable(user_repo.email_exists)
        assert callable(user_repo.update_user_status)
        assert callable(user_repo.deactivate_user)
        assert callable(user_repo.activate_user)
        assert callable(user_repo.verify_user)
        assert callable(user_repo.promote_to_superuser)
        assert callable(user_repo.demote_from_superuser)

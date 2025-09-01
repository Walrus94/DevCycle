"""
Unit tests for service factory functionality.

This module tests the ServiceFactory class and its service creation methods.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from devcycle.core.repositories.factory import RepositoryFactory
from devcycle.core.repositories.user_repository import UserRepository
from devcycle.core.services.factory import (
    ServiceFactory,
    get_service_factory,
    reset_service_factory,
)
from devcycle.core.services.user_service import UserService


@pytest.fixture
def mock_repository_factory():
    """Create a mock repository factory."""
    factory = MagicMock(spec=RepositoryFactory)
    factory.get_user_repository.return_value = AsyncMock(spec=UserRepository)
    return factory


@pytest.fixture
def service_factory(mock_repository_factory):
    """Create a service factory instance."""
    return ServiceFactory(mock_repository_factory)


class TestServiceFactory:
    """Test service factory functionality."""

    def test_init(self, mock_repository_factory):
        """Test factory initialization."""
        factory = ServiceFactory(mock_repository_factory)
        assert factory.repository_factory == mock_repository_factory
        assert factory._services == {}

    def test_get_user_service_first_time(
        self, service_factory, mock_repository_factory
    ):
        """Test getting user service for the first time."""
        # Act
        user_service = service_factory.get_user_service()

        # Assert
        assert isinstance(user_service, UserService)
        mock_repository_factory.get_user_repository.assert_called_once()
        assert UserService in service_factory._services

    def test_get_user_service_cached(self, service_factory, mock_repository_factory):
        """Test getting user service from cache."""
        # Arrange - Get service once to populate cache
        first_service = service_factory.get_user_service()

        # Act - Get service again
        second_service = service_factory.get_user_service()

        # Assert
        assert first_service is second_service  # Same instance
        # Only called once
        mock_repository_factory.get_user_repository.assert_called_once()

    def test_get_service_by_class(self, service_factory):
        """Test getting service by class."""
        # Act
        user_service = service_factory.get_service(UserService)

        # Assert
        assert isinstance(user_service, UserService)

    def test_get_service_unsupported_class(self, service_factory):
        """Test getting unsupported service class."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported service class"):
            service_factory.get_service(str)

    def test_create_service(self, service_factory, mock_repository_factory):
        """Test creating new service instance."""
        # Act
        user_service = service_factory.create_service(UserService)

        # Assert
        assert isinstance(user_service, UserService)
        mock_repository_factory.get_user_repository.assert_called_once()

    def test_create_service_unsupported_class(self, service_factory):
        """Test creating unsupported service class."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported service class"):
            service_factory.create_service(str)

    def test_reset_services(self, service_factory):
        """Test resetting service cache."""
        # Arrange - Populate cache
        service_factory.get_user_service()
        assert len(service_factory._services) > 0

        # Act
        service_factory.reset_services()

        # Assert
        assert len(service_factory._services) == 0


class TestGetServiceFactory:
    """Test get_service_factory function."""

    def test_get_service_factory_first_time(self, mock_repository_factory):
        """Test getting service factory for the first time."""
        # Act
        factory = get_service_factory(mock_repository_factory)

        # Assert
        assert isinstance(factory, ServiceFactory)
        # Check that the factory has a repository_factory attribute
        assert hasattr(factory, "repository_factory")
        # Check that it's the same instance we passed in
        assert factory.repository_factory is mock_repository_factory

    def test_get_service_factory_cached(self, mock_repository_factory):
        """Test getting cached service factory."""
        # Arrange - Get factory once
        first_factory = get_service_factory(mock_repository_factory)

        # Act - Get factory again
        second_factory = get_service_factory(mock_repository_factory)

        # Assert
        assert first_factory is second_factory  # Same instance

    def test_get_service_factory_default_repository(self):
        """Test getting service factory with default repository."""
        # Act
        factory = get_service_factory()

        # Assert
        assert isinstance(factory, ServiceFactory)

    def test_reset_service_factory(self, mock_repository_factory):
        """Test resetting service factory."""
        # Arrange - Get factory
        factory = get_service_factory(mock_repository_factory)

        # Act
        reset_service_factory()

        # Act - Get factory again
        new_factory = get_service_factory(mock_repository_factory)

        # Assert
        assert factory is not new_factory  # Different instances


class TestServiceFactoryIntegration:
    """Test service factory integration with repositories."""

    def test_user_service_through_factory(self, service_factory):
        """Test getting user service through factory."""
        # Act
        user_service = service_factory.get_user_service()

        # Assert
        assert isinstance(user_service, UserService)
        assert user_service.repository is not None

    def test_service_methods_accessible(self, service_factory):
        """Test that service methods are accessible through factory."""
        # Act
        user_service = service_factory.get_user_service()

        # Assert
        assert hasattr(user_service, "create_user")
        assert hasattr(user_service, "update_user_profile")
        assert hasattr(user_service, "deactivate_user")
        assert hasattr(user_service, "activate_user")
        assert hasattr(user_service, "verify_user_email")
        assert hasattr(user_service, "promote_to_superuser")
        assert hasattr(user_service, "get_active_users")
        assert hasattr(user_service, "search_users")
        assert hasattr(user_service, "validate_business_rules")
        assert hasattr(user_service, "apply_business_logic")

    def test_service_repository_dependency(
        self, service_factory, mock_repository_factory
    ):
        """Test that service has correct repository dependency."""
        # Act
        user_service = service_factory.get_user_service()

        # Assert
        assert user_service.repository == mock_repository_factory.get_user_repository()
        assert (
            user_service.user_repository
            == mock_repository_factory.get_user_repository()
        )

    def test_multiple_services_same_repository(
        self, service_factory, mock_repository_factory
    ):
        """Test that multiple services share the same repository factory."""
        # Act
        user_service1 = service_factory.get_user_service()
        user_service2 = service_factory.get_user_service()

        # Assert
        assert user_service1.repository == user_service2.repository
        assert user_service1.user_repository == user_service2.user_repository

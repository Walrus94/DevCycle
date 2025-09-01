"""
Service factory for DevCycle.

This module provides a factory for creating service instances
with proper dependency injection and configuration.
"""

from typing import Any, Dict, Optional, Type, TypeVar

from ..repositories.factory import RepositoryFactory
from .agent_service import AgentService
from .user_service import UserService

T = TypeVar("T")


class ServiceFactory:
    """
    Factory for creating service instances.

    This factory manages the creation of services with proper
    dependency injection and repository configuration.
    """

    def __init__(self, repository_factory: RepositoryFactory):
        """
        Initialize service factory.

        Args:
            repository_factory: Repository factory instance
        """
        self.repository_factory = repository_factory
        self._services: Dict[Type, Any] = {}

    def get_user_service(self) -> UserService:
        """
        Get user service instance.

        Returns:
            UserService instance
        """
        if UserService not in self._services:
            user_repository = self.repository_factory.get_user_repository()
            self._services[UserService] = UserService(user_repository)

        return self._services[UserService]  # type: ignore[no-any-return]

    def get_agent_service(self) -> AgentService:
        """
        Get agent service instance.

        Returns:
            AgentService instance
        """
        if AgentService not in self._services:
            agent_repository = self.repository_factory.get_agent_repository()
            task_repository = self.repository_factory.get_agent_task_repository()
            self._services[AgentService] = AgentService(
                agent_repository, task_repository
            )

        return self._services[AgentService]  # type: ignore[no-any-return]

    def get_service(self, service_class: Type[T], *args: Any, **kwargs: Any) -> T:
        """
        Get service instance by class.

        Args:
            service_class: Service class to instantiate

        Returns:
            Service instance

        Raises:
            ValueError: If service class is not supported
        """
        if service_class == UserService:
            return self.get_user_service()  # type: ignore[return-value]
        elif service_class == AgentService:
            return self.get_agent_service()  # type: ignore[return-value]

        raise ValueError(f"Unsupported service class: {service_class}")

    def create_service(self, service_class: Type[T], *args: Any, **kwargs: Any) -> T:
        """
        Create new service instance.

        Args:
            service_class: Service class to instantiate
            *args: Positional arguments for service constructor
            **kwargs: Keyword arguments for service constructor

        Returns:
            New service instance
        """
        if service_class == UserService:
            user_repository = self.repository_factory.get_user_repository()
            return UserService(
                user_repository, *args, **kwargs
            )  # type: ignore[return-value]
        elif service_class == AgentService:
            agent_repository = self.repository_factory.get_agent_repository()
            task_repository = self.repository_factory.get_agent_task_repository()
            return AgentService(
                agent_repository, task_repository, *args, **kwargs
            )  # type: ignore[return-value]

        raise ValueError(f"Unsupported service class: {service_class}")

    def reset_services(self) -> None:
        """Reset all cached service instances."""
        self._services.clear()


# Global service factory instance
_service_factory: Optional[ServiceFactory] = None


def get_service_factory(
    repository_factory: Optional[RepositoryFactory] = None,
) -> ServiceFactory:
    """
    Get global service factory instance.

    Args:
        repository_factory: Optional repository factory to use

    Returns:
        ServiceFactory instance
    """
    global _service_factory

    if _service_factory is None:
        if repository_factory is None:
            # Create default repository factory
            from ..repositories.factory import get_repository_factory

            repository_factory = get_repository_factory()  # type: ignore[call-arg]

        _service_factory = ServiceFactory(repository_factory)
    elif (
        repository_factory is not None
        and _service_factory.repository_factory is not repository_factory
    ):
        # If a different repository factory is provided, create a new service factory
        _service_factory = ServiceFactory(repository_factory)

    return _service_factory


def reset_service_factory() -> None:
    """Reset global service factory instance."""
    global _service_factory
    _service_factory = None

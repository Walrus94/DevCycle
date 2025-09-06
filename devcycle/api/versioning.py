"""
API versioning strategy and utilities.

This module provides utilities for managing API versions and ensuring
backward compatibility.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Request


class APIVersion(str, Enum):
    """Supported API versions."""

    V1 = "v1"
    V2 = "v2"  # Future version


class VersionedAPIRouter(APIRouter):
    """
    Versioned API router that automatically handles versioning.

    This router automatically adds version prefixes and handles
    version-specific routing.
    """

    def __init__(
        self,
        version: APIVersion = APIVersion.V1,
        prefix: str = "",
        tags: Optional[List[Union[str, Enum]]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize versioned router."""
        # Add version prefix
        versioned_prefix = f"/api/{version.value}"
        if prefix:
            versioned_prefix += prefix

        super().__init__(prefix=versioned_prefix, tags=tags or [], **kwargs)
        self.version = version


def get_api_version(request: Request) -> APIVersion:
    """
    Extract API version from request.

    Args:
        request: FastAPI request object

    Returns:
        API version
    """
    path_parts = request.url.path.split("/")

    # Look for /api/v1, /api/v2, etc.
    if len(path_parts) >= 3 and path_parts[1] == "api":
        version_str = path_parts[2]
        try:
            return APIVersion(version_str)
        except ValueError:
            # Default to v1 if version is not recognized
            return APIVersion.V1

    return APIVersion.V1


def get_version_info() -> Dict[str, Any]:
    """
    Get current API version information.

    Returns:
        Dictionary with version information
    """
    return {
        "current_version": APIVersion.V1.value,
        "supported_versions": [version.value for version in APIVersion],
        "deprecated_versions": [],  # Add deprecated versions here
        "versioning_strategy": "URL path versioning",
        "deprecation_policy": (
            "Versions are supported for at least 12 months after deprecation"
        ),
    }


def create_versioned_router(
    version: APIVersion = APIVersion.V1,
    prefix: str = "",
    tags: Optional[List[Union[str, Enum]]] = None,
    **kwargs: Any,
) -> VersionedAPIRouter:
    """
    Create a versioned API router.

    Args:
        version: API version
        prefix: Router prefix (will be added after version prefix)
        tags: OpenAPI tags
        **kwargs: Additional router arguments

    Returns:
        Versioned API router
    """
    return VersionedAPIRouter(version=version, prefix=prefix, tags=tags, **kwargs)

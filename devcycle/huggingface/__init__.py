"""
Hugging Face integration for DevCycle AI agents.

This module provides functionality for managing Hugging Face workspaces,
spaces, and API integrations.
"""

from typing import Optional

from .client import HuggingFaceClient
from .space import HuggingFaceSpace
from .workspace import HuggingFaceWorkspace, WorkspaceConfig

# Import CLI functions only when needed to avoid import issues in CI
try:
    from .cli import check_workspace_status, setup_workspace

    _CLI_AVAILABLE = True
except ImportError as e:
    _CLI_AVAILABLE = False
    _import_error = str(e)

    # Define placeholder functions to avoid import errors
    def setup_workspace(
        org_name: str,
        description: str,
        visibility: str = "public",
        token: Optional[str] = None,
    ) -> bool:
        """Set up a Hugging Face workspace."""
        raise ImportError(f"CLI module not available: {_import_error}")

    def check_workspace_status(org_name: str, token: Optional[str] = None) -> bool:
        """Check the status of a Hugging Face workspace."""
        raise ImportError(f"CLI module not available: {_import_error}")


__all__ = [
    "HuggingFaceWorkspace",
    "WorkspaceConfig",
    "HuggingFaceSpace",
    "HuggingFaceClient",
    "setup_workspace",
    "check_workspace_status",
]

"""
Hugging Face workspace management for DevCycle.

This module provides workspace-level operations including organization
management, user permissions, and branding configuration.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..core.logging import get_logger
from .client import HuggingFaceClient


@dataclass
class WorkspaceConfig:
    """Configuration for a Hugging Face workspace."""

    name: str
    description: str
    visibility: str = "public"  # public, private
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    tags: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Initialize the workspace config after creation."""
        if self.tags is None:
            self.tags = []


class HuggingFaceWorkspace:
    """
    Manages Hugging Face workspace operations for DevCycle.

    This class handles workspace creation, configuration, and management.
    """

    def __init__(self, client: HuggingFaceClient):
        """
        Initialize the workspace manager.

        Args:
            client: Hugging Face API client
        """
        self.client = client
        self.logger = get_logger("huggingface.workspace")
        self.logger.info("Hugging Face workspace manager initialized")

    def setup_devcycle_workspace(self, config: WorkspaceConfig) -> bool:
        """
        Set up the DevCycle workspace with proper configuration.

        Args:
            config: Workspace configuration

        Returns:
            True if setup is successful, False otherwise
        """
        try:
            self.logger.info(f"Setting up DevCycle workspace: {config.name}")

            # Test connection first
            if not self.client.test_connection():
                self.logger.error("Failed to connect to Hugging Face API")
                return False

            # Check if organization exists
            orgs = self.client.get_organizations()
            org_names = [org.get("name", "") for org in orgs]

            if config.name in org_names:
                self.logger.info(f"Organization {config.name} already exists")
                return self._configure_existing_workspace(config)
            else:
                self.logger.info(f"Organization {config.name} does not exist")
                return self._create_new_workspace(config)

        except Exception as e:
            self.logger.error(f"Failed to setup DevCycle workspace: {e}")
            return False

    def _create_new_workspace(self, config: WorkspaceConfig) -> bool:
        """
        Create a new DevCycle workspace.

        Args:
            config: Workspace configuration

        Returns:
            True if creation is successful, False otherwise
        """
        try:
            self.logger.info(f"Creating new workspace: {config.name}")

            # Note: Organization creation requires manual setup through web interface
            # We'll log instructions for the user
            self.logger.warning(
                f"Please create organization '{config.name}' manually through "
                "Hugging Face web interface at https://huggingface.co/organizations/new"
            )

            # For now, we'll assume the organization will be created manually
            # and focus on configuration
            return self._configure_existing_workspace(config)

        except Exception as e:
            self.logger.error(f"Failed to create new workspace: {e}")
            return False

    def _configure_existing_workspace(self, config: WorkspaceConfig) -> bool:
        """
        Configure an existing DevCycle workspace.

        Args:
            config: Workspace configuration

        Returns:
            True if configuration is successful, False otherwise
        """
        try:
            self.logger.info(f"Configuring existing workspace: {config.name}")

            # Create the main DevCycle space
            space_repo_id = f"{config.name}/devcycle-ai-agents"

            # Check if space already exists
            existing_spaces = self.client.get_spaces(config.name)
            space_exists = any(
                space.get("id") == space_repo_id for space in existing_spaces
            )

            if space_exists:
                self.logger.info(f"Space {space_repo_id} already exists")
                return self._update_space_config(space_repo_id, config)
            else:
                self.logger.info(f"Creating new space: {space_repo_id}")
                return self._create_devcycle_space(space_repo_id, config)

        except Exception as e:
            self.logger.error(f"Failed to configure existing workspace: {e}")
            return False

    def _create_devcycle_space(self, repo_id: str, config: WorkspaceConfig) -> bool:
        """
        Create the main DevCycle AI agents space.

        Args:
            repo_id: Repository ID for the space
            config: Workspace configuration

        Returns:
            True if creation is successful, False otherwise
        """
        try:
            self.logger.info(f"Creating DevCycle space: {repo_id}")

            # Create the space with Gradio (good for interactive demos)
            space_info = self.client.create_space(
                repo_id=repo_id,
                space_sdk="gradio",
                space_hardware="cpu-basic",
                private=(config.visibility == "private"),
            )

            if space_info:
                self.logger.info(f"Successfully created space: {repo_id}")
                return self._update_space_config(repo_id, config)
            else:
                self.logger.error(f"Failed to create space: {repo_id}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to create DevCycle space: {e}")
            return False

    def _update_space_config(self, repo_id: str, config: WorkspaceConfig) -> bool:
        """
        Update space configuration with DevCycle branding.

        Args:
            repo_id: Repository ID
            config: Workspace configuration

        Returns:
            True if update is successful, False otherwise
        """
        try:
            self.logger.info(f"Updating space configuration: {repo_id}")

            # Create configuration dictionary
            base_tags = config.tags or []
            space_config = {
                "name": "DevCycle AI Agents",
                "description": config.description,
                "tags": base_tags + ["ai", "agents", "development", "automation"],
                "visibility": config.visibility,
                "logo_url": config.logo_url,
                "website_url": config.website_url,
            }

            # Update the space configuration
            success = self.client.update_space_config(repo_id, space_config)

            if success:
                self.logger.info(f"Successfully updated space configuration: {repo_id}")
                return True
            else:
                self.logger.error(f"Failed to update space configuration: {repo_id}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to update space configuration: {e}")
            return False

    def get_workspace_status(self, org_name: str) -> Dict[str, Any]:
        """
        Get the current status of the DevCycle workspace.

        Args:
            org_name: Organization name

        Returns:
            Dictionary containing workspace status information
        """
        try:
            self.logger.info(f"Getting workspace status for: {org_name}")

            # Get organizations
            orgs = self.client.get_organizations()
            org = next((org for org in orgs if org.get("name") == org_name), None)

            if not org:
                return {
                    "exists": False,
                    "status": "not_found",
                    "message": f"Organization {org_name} not found",
                }

            # Get spaces
            spaces = self.client.get_spaces(org_name)
            devcycle_space = next(
                (
                    space
                    for space in spaces
                    if "devcycle" in space.get("id", "").lower()
                ),
                None,
            )

            return {
                "exists": True,
                "organization": org,
                "spaces_count": len(spaces),
                "devcycle_space": devcycle_space,
                "status": "active" if devcycle_space else "incomplete",
            }

        except Exception as e:
            self.logger.error(f"Failed to get workspace status: {e}")
            return {"exists": False, "status": "error", "message": str(e)}

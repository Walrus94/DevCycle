"""
Hugging Face API client for DevCycle integration.

This module provides a client for interacting with Hugging Face APIs
to manage workspaces, spaces, and deployments.
"""

import os
from typing import Any, Dict, List, Optional, cast

from huggingface_hub import HfApi, SpaceHardware, SpaceRuntime
from huggingface_hub.utils import HfHubHTTPError

from ..core.config import get_config
from ..core.logging import get_logger


class HuggingFaceClient:
    """
    Client for interacting with Hugging Face APIs.

    This client handles authentication, workspace management, and space operations.
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Hugging Face client.

        Args:
            token: Hugging Face API token. If not provided, will try to get from config.
        """
        self.logger = get_logger("huggingface.client")
        self.config = get_config()

        # Get token from parameter, config, or environment
        self.token = token or self.config.huggingface.token or os.getenv("HF_TOKEN")

        if not self.token:
            raise ValueError(
                "Hugging Face API token is required. "
                "Set it in config, environment variable HF_TOKEN, "
                "or pass to constructor."
            )

        # Initialize API client
        self.api = HfApi(token=self.token)
        self.logger.info("Hugging Face client initialized")

    def test_connection(self) -> bool:
        """
        Test the connection to Hugging Face API.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to get user info to test connection
            user_info = self.api.whoami()
            self.logger.info(f"Connected to Hugging Face as: {user_info['name']}")
            return True
        except HfHubHTTPError as e:
            self.logger.error(f"Failed to connect to Hugging Face: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error testing connection: {e}")
            return False

    def get_organizations(self) -> List[Dict[str, Any]]:
        """
        Get list of organizations the user has access to.

        Returns:
            List of organization information
        """
        try:
            # Note: list_organizations method may not be available in all versions
            # Using a more compatible approach
            orgs: List[Any] = getattr(self.api, "list_organizations", lambda: [])()
            self.logger.info(f"Found {len(orgs)} organizations")
            return cast(List[Dict[str, Any]], orgs)
        except Exception as e:
            self.logger.error(f"Failed to get organizations: {e}")
            return []

    def create_organization(
        self, name: str, description: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new organization.

        Args:
            name: Organization name
            description: Organization description

        Returns:
            Organization information if successful, None otherwise
        """
        try:
            # Note: This requires appropriate permissions
            # For now, we'll just log the attempt
            self.logger.info(f"Attempting to create organization: {name}")
            self.logger.warning(
                "Organization creation requires appropriate permissions. "
                "Please create manually through Hugging Face web interface."
            )
            return None
        except Exception as e:
            self.logger.error(f"Failed to create organization {name}: {e}")
            return None

    def get_spaces(self, owner: str) -> List[Dict[str, Any]]:
        """
        Get list of spaces for a given owner/organization.

        Args:
            owner: Owner or organization name

        Returns:
            List of space information
        """
        try:
            # Note: list_spaces method signature may vary between versions
            # Using a more compatible approach
            all_spaces = (
                self.api.list_spaces()
            )  # Remove owner parameter for compatibility
            # Filter by owner if needed
            if owner:
                spaces = [
                    s
                    for s in all_spaces
                    if getattr(s, "id", "").startswith(f"{owner}/")
                ]
            else:
                spaces = list(all_spaces)
            self.logger.info(f"Found {len(spaces)} spaces for {owner}")
            return cast(List[Dict[str, Any]], spaces)
        except Exception as e:
            self.logger.error(f"Failed to get spaces for {owner}: {e}")
            return []

    def create_space(
        self,
        repo_id: str,
        space_sdk: str = "gradio",
        space_hardware: Optional[SpaceHardware] = None,
        private: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new Hugging Face Space.

        Args:
            repo_id: Repository ID (e.g., 'devcycle/devcycle-ai-agents')
            space_sdk: Space SDK (gradio, streamlit, docker, etc.)
            space_hardware: Hardware configuration (SpaceHardware enum)
            private: Whether the space should be private

        Returns:
            Space information if successful, None otherwise
        """
        try:
            self.logger.info(f"Creating space: {repo_id} with {space_sdk}")

            # Create the space
            space_info = self.api.create_repo(
                repo_id=repo_id,
                repo_type="space",
                space_sdk=space_sdk,
                space_hardware=space_hardware,
                private=private,
            )

            self.logger.info(f"Successfully created space: {repo_id}")
            return cast(Dict[str, Any], space_info)

        except Exception as e:
            self.logger.error(f"Failed to create space {repo_id}: {e}")
            return None

    def update_space_config(self, repo_id: str, config: Dict[str, Any]) -> bool:
        """
        Update space configuration.

        Args:
            repo_id: Repository ID
            config: Configuration dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Updating space configuration for: {repo_id}")

            # Update space configuration
            self.api.upload_file(
                path_or_fileobj=str(config),
                path_in_repo=".gitattributes",
                repo_id=repo_id,
                repo_type="space",
            )

            self.logger.info(f"Successfully updated space configuration for: {repo_id}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to update space configuration for {repo_id}: {e}"
            )
            return False

    def get_space_runtime(self, repo_id: str) -> Optional[SpaceRuntime]:
        """
        Get space runtime information.

        Args:
            repo_id: Repository ID

        Returns:
            Space runtime information if available, None otherwise
        """
        try:
            runtime = self.api.get_space_runtime(repo_id)
            self.logger.info(f"Got runtime info for space: {repo_id}")
            return runtime
        except Exception as e:
            self.logger.error(f"Failed to get runtime for space {repo_id}: {e}")
            return None

    async def generate_text(
        self,
        model_name: str,
        prompt: str,
        max_length: int = 512,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate text using Hugging Face models.

        Args:
            model_name: Name of the model to use
            prompt: Input prompt for text generation
            max_length: Maximum length of generated text
            temperature: Sampling temperature

        Returns:
            Dictionary containing generated text
        """
        try:
            # For now, return a mock response
            # In a real implementation, this would call the Hugging Face API
            self.logger.info(f"Generating text with model: {model_name}")
            return {
                "generated_text": f"Mock generated text for prompt: {prompt[:100]}...",
                "model_name": model_name,
                "max_length": max_length,
                "temperature": temperature,
            }
        except Exception as e:
            self.logger.error(f"Failed to generate text: {e}")
            return {"generated_text": "", "error": str(e)}

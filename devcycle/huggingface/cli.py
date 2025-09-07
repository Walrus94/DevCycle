"""
CLI for Hugging Face workspace management.

This module provides command-line interface for setting up and managing
DevCycle Hugging Face workspaces.
"""

import argparse
import sys
from typing import Optional

from ..core.logging import get_logger, setup_logging
from .client import HuggingFaceClient
from .workspace import HuggingFaceWorkspace, WorkspaceConfig


def setup_workspace(
    org_name: str,
    description: str,
    visibility: str = "public",
    token: Optional[str] = None,
) -> bool:
    """
    Set up the DevCycle Hugging Face workspace.

    Args:
        org_name: Organization name
        description: Workspace description
        visibility: Workspace visibility (public/private)
        token: Hugging Face API token

    Returns:
        True if setup is successful, False otherwise
    """
    try:
        logger = get_logger("huggingface.cli")
        logger.info(f"Setting up DevCycle workspace: {org_name}")

        # Initialize client
        client = HuggingFaceClient(token=token)

        # Test connection
        if not client.test_connection():
            logger.error("Failed to connect to Hugging Face API")
            return False

        # Create workspace configuration
        config = WorkspaceConfig(
            name=org_name,
            description=description,
            visibility=visibility,
            tags=["ai", "agents", "development", "automation", "devcycle"],
        )

        # Initialize workspace manager
        workspace = HuggingFaceWorkspace(client)

        # Setup workspace
        success = workspace.setup_devcycle_workspace(config)

        if success:
            logger.info(f"Successfully set up DevCycle workspace: {org_name}")

            # Get and display status
            status = workspace.get_workspace_status(org_name)
            logger.info(f"Workspace status: {status}")

            return True
        else:
            logger.error(f"Failed to setup DevCycle workspace: {org_name}")
            return False

    except Exception as e:
        logger.error(f"Unexpected error during workspace setup: {e}")
        return False


def check_workspace_status(org_name: str, token: Optional[str] = None) -> bool:
    """
    Check the status of an existing DevCycle workspace.

    Args:
        org_name: Organization name
        token: Hugging Face API token

    Returns:
        True if status check is successful, False otherwise
    """
    try:
        logger = get_logger("huggingface.cli")
        logger.info(f"Checking workspace status: {org_name}")

        # Initialize client
        client = HuggingFaceClient(token=token)

        # Test connection
        if not client.test_connection():
            logger.error("Failed to connect to Hugging Face API")
            return False

        # Initialize workspace manager
        workspace = HuggingFaceWorkspace(client)

        # Get status
        status = workspace.get_workspace_status(org_name)

        # Display status
        logger.info("Workspace Status:")
        for key, value in status.items():
            logger.info(f"  {key}: {value}")

        return True

    except Exception as e:
        logger.error(f"Unexpected error during status check: {e}")
        return False


def main() -> None:
    """Run the main CLI entry point."""
    # Setup logging
    setup_logging(json_output=False)  # Human-readable for CLI

    parser = argparse.ArgumentParser(
        description="DevCycle Hugging Face Workspace Manager"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Setup DevCycle workspace")
    setup_parser.add_argument("org_name", help="Organization name")
    setup_parser.add_argument("description", help="Workspace description")
    setup_parser.add_argument(
        "--visibility",
        choices=["public", "private"],
        default="public",
        help="Workspace visibility",
    )
    setup_parser.add_argument(
        "--token", help="Hugging Face API token (or set HF_TOKEN env var)"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Check workspace status")
    status_parser.add_argument("org_name", help="Organization name")
    status_parser.add_argument(
        "--token", help="Hugging Face API token (or set HF_TOKEN env var)"
    )

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    if args.command == "setup":
        success = setup_workspace(
            org_name=args.org_name,
            description=args.description,
            visibility=args.visibility,
            token=args.token,
        )
        sys.exit(0 if success else 1)

    elif args.command == "status":
        success = check_workspace_status(org_name=args.org_name, token=args.token)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

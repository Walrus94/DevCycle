#!/usr/bin/env python3
"""
Example script for setting up DevCycle Hugging Face workspace.

This script demonstrates how to use the Hugging Face integration
to set up a workspace and create spaces for AI agents.
"""

import os
import sys
from pathlib import Path

try:
    from devcycle.huggingface import (
        HuggingFaceClient,
        HuggingFaceWorkspace,
        WorkspaceConfig,
        check_workspace_status,
        setup_workspace,
    )
except ImportError:
    # Add the project root to the path if import fails
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    from devcycle.huggingface import (
        HuggingFaceClient,
        HuggingFaceWorkspace,
        WorkspaceConfig,
        check_workspace_status,
        setup_workspace,
    )


def main() -> None:
    """Main example function."""
    print("DevCycle Hugging Face Workspace Setup Example")
    print("=" * 50)

    # Get API token from environment
    token = os.getenv("HF_TOKEN")
    if not token:
        print("Error: HF_TOKEN environment variable not set")
        print("Please set your Hugging Face API token:")
        print("export HF_TOKEN='your-token-here'")
        return

    # Organization configuration
    org_name = "devcycle"  # Change this to your desired organization name
    description = "AI-Powered Application Development Lifecycle Automation System"

    print(f"Setting up workspace for organization: {org_name}")
    print(f"Description: {description}")
    print()

    try:
        # Option 1: Use the high-level setup function
        print("Option 1: Using high-level setup function")
        print("-" * 40)

        success = setup_workspace(
            org_name=org_name, description=description, visibility="public", token=token
        )

        if success:
            print("✅ Workspace setup completed successfully!")
        else:
            print("❌ Workspace setup failed")

        print()

        # Option 2: Use the classes directly for more control
        print("Option 2: Using classes directly")
        print("-" * 40)

        # Initialize client
        client = HuggingFaceClient(token=token)

        # Test connection
        if client.test_connection():
            print("✅ Connected to Hugging Face API")

            # Get organizations
            orgs = client.get_organizations()
            print(f"Found {len(orgs)} organizations:")
            for org in orgs:
                print(f"  - {org.get('name', 'Unknown')}")

            # Initialize workspace manager
            workspace = HuggingFaceWorkspace(client)

            # Create workspace configuration
            config = WorkspaceConfig(
                name=org_name,
                description=description,
                visibility="public",
                tags=["ai", "agents", "development", "automation", "devcycle"],
            )

            # Setup workspace
            success = workspace.setup_devcycle_workspace(config)

            if success:
                print("✅ Workspace setup completed successfully!")

                # Check status
                status = workspace.get_workspace_status(org_name)
                print("Workspace Status:")
                for key, value in status.items():
                    print(f"  {key}: {value}")
            else:
                print("❌ Workspace setup failed")
        else:
            print("❌ Failed to connect to Hugging Face API")

        print()

        # Check final status
        print("Final Status Check")
        print("-" * 40)

        check_workspace_status(org_name, token)

    except Exception as e:
        print(f"❌ Error during workspace setup: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

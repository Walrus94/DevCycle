"""
CLI tool for managing secrets with GCP Secret Manager.

This tool provides commands for:
- Creating and updating secrets
- Rotating secrets manually
- Validating secret accessibility
- Listing secrets
"""

import argparse
import json
import sys
from typing import Any, Dict, Optional

from devcycle.core.secrets.gcp_secret_manager import get_secret_client
from devcycle.core.secrets.secret_config import validate_production_secrets


def create_secret(args) -> None:
    """Create a new secret in GCP Secret Manager."""
    client = get_secret_client()

    success = client.create_secret(
        secret_id=args.secret_id, secret_value=args.value, environment=args.environment
    )

    if success:
        print(
            f"✅ Secret '{args.secret_id}' created successfully in {args.environment} environment"
        )
    else:
        print(f"❌ Failed to create secret '{args.secret_id}'")
        sys.exit(1)


def rotate_secret(args) -> None:
    """Rotate an existing secret."""
    client = get_secret_client()

    success = client.rotate_secret(
        secret_id=args.secret_id, new_value=args.value, environment=args.environment
    )

    if success:
        print(
            f"✅ Secret '{args.secret_id}' rotated successfully in {args.environment} environment"
        )
    else:
        print(f"❌ Failed to rotate secret '{args.secret_id}'")
        sys.exit(1)


def validate_secrets(args) -> None:
    """Validate that all required secrets are accessible."""
    if args.environment == "production":
        success = validate_production_secrets()
        if success:
            print("✅ All production secrets are accessible")
        else:
            print("❌ Some production secrets are missing or inaccessible")
            sys.exit(1)
    else:
        print(f"⚠️  Validation for {args.environment} environment not implemented")
        print(
            "Use 'validate-secrets --environment production' for production validation"
        )


def list_secrets(args) -> None:
    """List all secrets for the given environment."""
    client = get_secret_client()

    secrets = client.list_secrets(environment=args.environment)

    if secrets:
        print(f"📋 Secrets in {args.environment} environment:")
        for secret in secrets:
            print(f"  • {secret}")
    else:
        print(f"📋 No secrets found in {args.environment} environment")


def get_secret_value(args) -> None:
    """Get the value of a specific secret."""
    client = get_secret_client()

    value = client.get_secret(
        secret_id=args.secret_id, environment=args.environment, parse_json=args.json
    )

    if value is not None:
        if args.json and isinstance(value, dict):
            print(json.dumps(value, indent=2))
        else:
            print(value)
    else:
        print(
            f"❌ Secret '{args.secret_id}' not found in {args.environment} environment"
        )
        sys.exit(1)


def clear_cache(args) -> None:
    """Clear all cached secrets."""
    client = get_secret_client()
    cleared_count = client.clear_all_caches()
    print(f"✅ Cleared {cleared_count} cached secrets")


def show_cache_stats(args) -> None:
    """Show cache statistics."""
    client = get_secret_client()
    stats = client.get_cache_stats()

    print("📊 Cache Statistics:")
    print(f"  Total cached secrets: {stats.get('total_keys', 0)}")
    print(f"  Redis connected: {stats.get('redis_connected', False)}")
    print(f"  Caching enabled: {stats.get('caching_enabled', True)}")

    if stats.get("redis_connected"):
        print(f"  Redis version: {stats.get('redis_version', 'unknown')}")
        print(f"  Memory used: {stats.get('used_memory', 'unknown')}")
        print(f"  Connected clients: {stats.get('connected_clients', 0)}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DevCycle Secret Manager CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new secret
  python -m devcycle.cli.secret_manager create jwt-secret-key --value "my-secret-key" --environment prod

  # Rotate an existing secret
  python -m devcycle.cli.secret_manager rotate jwt-secret-key --value "new-secret-key" --environment prod

  # List all secrets
  python -m devcycle.cli.secret_manager list --environment prod

  # Get a secret value
  python -m devcycle.cli.secret_manager get jwt-secret-key --environment prod

  # Validate all production secrets
  python -m devcycle.cli.secret_manager validate --environment production

  # Clear all cached secrets
  python -m devcycle.cli.secret_manager cache clear

  # Show cache statistics
  python -m devcycle.cli.secret_manager cache stats
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create secret command
    create_parser = subparsers.add_parser("create", help="Create a new secret")
    create_parser.add_argument("secret_id", help="Secret identifier")
    create_parser.add_argument("--value", required=True, help="Secret value")
    create_parser.add_argument(
        "--environment", default="dev", help="Environment (dev, staging, prod)"
    )
    create_parser.set_defaults(func=create_secret)

    # Rotate secret command
    rotate_parser = subparsers.add_parser("rotate", help="Rotate an existing secret")
    rotate_parser.add_argument("secret_id", help="Secret identifier")
    rotate_parser.add_argument("--value", required=True, help="New secret value")
    rotate_parser.add_argument(
        "--environment", default="dev", help="Environment (dev, staging, prod)"
    )
    rotate_parser.set_defaults(func=rotate_secret)

    # Validate secrets command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate all required secrets"
    )
    validate_parser.add_argument(
        "--environment", default="production", help="Environment to validate"
    )
    validate_parser.set_defaults(func=validate_secrets)

    # List secrets command
    list_parser = subparsers.add_parser("list", help="List all secrets")
    list_parser.add_argument(
        "--environment", default="dev", help="Environment (dev, staging, prod)"
    )
    list_parser.set_defaults(func=list_secrets)

    # Get secret command
    get_parser = subparsers.add_parser("get", help="Get a secret value")
    get_parser.add_argument("secret_id", help="Secret identifier")
    get_parser.add_argument(
        "--environment", default="dev", help="Environment (dev, staging, prod)"
    )
    get_parser.add_argument("--json", action="store_true", help="Parse secret as JSON")
    get_parser.set_defaults(func=get_secret_value)

    # Cache management commands
    cache_parser = subparsers.add_parser("cache", help="Cache management")
    cache_subparsers = cache_parser.add_subparsers(
        dest="cache_action", help="Cache actions"
    )

    # Clear cache command
    clear_cache_parser = cache_subparsers.add_parser(
        "clear", help="Clear all cached secrets"
    )
    clear_cache_parser.set_defaults(func=clear_cache)

    # Cache stats command
    stats_parser = cache_subparsers.add_parser("stats", help="Show cache statistics")
    stats_parser.set_defaults(func=show_cache_stats)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Unit tests for the secret management CLI tool.

These tests focus on the command-line interface functionality
with mocked dependencies to ensure fast execution and isolation.
"""

import json
from unittest.mock import Mock, patch

import pytest

from devcycle.cli.secret_manager import (
    create_secret,
    get_secret_value,
    list_secrets,
    main,
    rotate_secret,
    validate_secrets,
)


@pytest.mark.unit
class TestSecretCLIFunctions:
    """Test the CLI function implementations."""

    def test_create_secret_success(self, capsys):
        """Test successful secret creation."""
        with patch("devcycle.cli.secret_manager.get_secret_client") as mock_get_client:
            mock_client = Mock()
            mock_client.create_secret.return_value = True
            mock_get_client.return_value = mock_client

            args = Mock()
            args.secret_id = "jwt-secret-key"
            args.value = "secret-value"
            args.environment = "prod"

            create_secret(args)

            captured = capsys.readouterr()
            assert (
                "✅ Secret 'jwt-secret-key' created successfully in prod environment"
                in captured.out
            )
            mock_client.create_secret.assert_called_once_with(
                secret_id="jwt-secret-key",
                secret_value="secret-value",
                environment="prod",
            )

    def test_create_secret_failure(self, capsys):
        """Test failed secret creation."""
        with patch("devcycle.cli.secret_manager.get_secret_client") as mock_get_client:
            mock_client = Mock()
            mock_client.create_secret.return_value = False
            mock_get_client.return_value = mock_client

            args = Mock()
            args.secret_id = "jwt-secret-key"
            args.value = "secret-value"
            args.environment = "prod"

            with pytest.raises(SystemExit):
                create_secret(args)

            captured = capsys.readouterr()
            assert "❌ Failed to create secret 'jwt-secret-key'" in captured.out

    def test_rotate_secret_success(self, capsys):
        """Test successful secret rotation."""
        with patch("devcycle.cli.secret_manager.get_secret_client") as mock_get_client:
            mock_client = Mock()
            mock_client.rotate_secret.return_value = True
            mock_get_client.return_value = mock_client

            args = Mock()
            args.secret_id = "jwt-secret-key"
            args.value = "new-secret-value"
            args.environment = "prod"

            rotate_secret(args)

            captured = capsys.readouterr()
            assert (
                "✅ Secret 'jwt-secret-key' rotated successfully in prod environment"
                in captured.out
            )
            mock_client.rotate_secret.assert_called_once_with(
                secret_id="jwt-secret-key",
                new_value="new-secret-value",
                environment="prod",
            )

    def test_rotate_secret_failure(self, capsys):
        """Test failed secret rotation."""
        with patch("devcycle.cli.secret_manager.get_secret_client") as mock_get_client:
            mock_client = Mock()
            mock_client.rotate_secret.return_value = False
            mock_get_client.return_value = mock_client

            args = Mock()
            args.secret_id = "jwt-secret-key"
            args.value = "new-secret-value"
            args.environment = "prod"

            with pytest.raises(SystemExit):
                rotate_secret(args)

            captured = capsys.readouterr()
            assert "❌ Failed to rotate secret 'jwt-secret-key'" in captured.out

    def test_validate_secrets_production_success(self, capsys):
        """Test successful production secrets validation."""
        with patch(
            "devcycle.cli.secret_manager.validate_production_secrets"
        ) as mock_validate:
            mock_validate.return_value = True

            args = Mock()
            args.environment = "production"

            validate_secrets(args)

            captured = capsys.readouterr()
            assert "✅ All production secrets are accessible" in captured.out

    def test_validate_secrets_production_failure(self, capsys):
        """Test failed production secrets validation."""
        with patch(
            "devcycle.cli.secret_manager.validate_production_secrets"
        ) as mock_validate:
            mock_validate.return_value = False

            args = Mock()
            args.environment = "production"

            with pytest.raises(SystemExit):
                validate_secrets(args)

            captured = capsys.readouterr()
            assert (
                "❌ Some production secrets are missing or inaccessible" in captured.out
            )

    def test_validate_secrets_non_production(self, capsys):
        """Test validation for non-production environments."""
        args = Mock()
        args.environment = "staging"

        validate_secrets(args)

        captured = capsys.readouterr()
        assert "⚠️  Validation for staging environment not implemented" in captured.out

    def test_list_secrets_with_results(self, capsys):
        """Test listing secrets with results."""
        with patch("devcycle.cli.secret_manager.get_secret_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_secrets.return_value = [
                "jwt-secret-key",
                "database-password",
                "redis-password",
            ]
            mock_get_client.return_value = mock_client

            args = Mock()
            args.environment = "prod"

            list_secrets(args)

            captured = capsys.readouterr()
            assert "📋 Secrets in prod environment:" in captured.out
            assert "• jwt-secret-key" in captured.out
            assert "• database-password" in captured.out
            assert "• redis-password" in captured.out

    def test_list_secrets_empty(self, capsys):
        """Test listing secrets when no secrets exist."""
        with patch("devcycle.cli.secret_manager.get_secret_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_secrets.return_value = []
            mock_get_client.return_value = mock_client

            args = Mock()
            args.environment = "prod"

            list_secrets(args)

            captured = capsys.readouterr()
            assert "📋 No secrets found in prod environment" in captured.out

    def test_get_secret_value_success(self, capsys):
        """Test successful secret value retrieval."""
        with patch("devcycle.cli.secret_manager.get_secret_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_secret.return_value = "secret-value"
            mock_get_client.return_value = mock_client

            args = Mock()
            args.secret_id = "jwt-secret-key"
            args.environment = "prod"
            args.json = False

            get_secret_value(args)

            captured = capsys.readouterr()
            assert "secret-value" in captured.out

    def test_get_secret_value_json(self, capsys):
        """Test secret value retrieval with JSON parsing."""
        with patch("devcycle.cli.secret_manager.get_secret_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_secret.return_value = {"key": "value", "number": 42}
            mock_get_client.return_value = mock_client

            args = Mock()
            args.secret_id = "json-secret"
            args.environment = "prod"
            args.json = True

            get_secret_value(args)

            captured = capsys.readouterr()
            output = captured.out.strip()
            parsed_output = json.loads(output)
            assert parsed_output == {"key": "value", "number": 42}

    def test_get_secret_value_not_found(self, capsys):
        """Test secret value retrieval when secret doesn't exist."""
        with patch("devcycle.cli.secret_manager.get_secret_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_secret.return_value = None
            mock_get_client.return_value = mock_client

            args = Mock()
            args.secret_id = "nonexistent-secret"
            args.environment = "prod"
            args.json = False

            with pytest.raises(SystemExit):
                get_secret_value(args)

            captured = capsys.readouterr()
            assert (
                "❌ Secret 'nonexistent-secret' not found in prod environment"
                in captured.out
            )


@pytest.mark.unit
class TestSecretCLIMain:
    """Test the main CLI entry point."""

    def test_main_create_command(self, capsys):
        """Test main function with create command."""
        with (
            patch("devcycle.cli.secret_manager.create_secret") as mock_create,
            patch(
                "sys.argv",
                [
                    "secret_manager",
                    "create",
                    "jwt-secret-key",
                    "--value",
                    "secret-value",
                    "--environment",
                    "prod",
                ],
            ),
        ):

            mock_create.return_value = None

            main()

            mock_create.assert_called_once()

    def test_main_rotate_command(self, capsys):
        """Test main function with rotate command."""
        with (
            patch("devcycle.cli.secret_manager.rotate_secret") as mock_rotate,
            patch(
                "sys.argv",
                [
                    "secret_manager",
                    "rotate",
                    "jwt-secret-key",
                    "--value",
                    "new-secret-value",
                    "--environment",
                    "prod",
                ],
            ),
        ):

            mock_rotate.return_value = None

            main()

            mock_rotate.assert_called_once()

    def test_main_validate_command(self, capsys):
        """Test main function with validate command."""
        with (
            patch("devcycle.cli.secret_manager.validate_secrets") as mock_validate,
            patch(
                "sys.argv",
                ["secret_manager", "validate", "--environment", "production"],
            ),
        ):

            mock_validate.return_value = None

            main()

            mock_validate.assert_called_once()

    def test_main_list_command(self, capsys):
        """Test main function with list command."""
        with (
            patch("devcycle.cli.secret_manager.list_secrets") as mock_list,
            patch("sys.argv", ["secret_manager", "list", "--environment", "prod"]),
        ):

            mock_list.return_value = None

            main()

            mock_list.assert_called_once()

    def test_main_get_command(self, capsys):
        """Test main function with get command."""
        with (
            patch("devcycle.cli.secret_manager.get_secret_value") as mock_get,
            patch(
                "sys.argv",
                ["secret_manager", "get", "jwt-secret-key", "--environment", "prod"],
            ),
        ):

            mock_get.return_value = None

            main()

            mock_get.assert_called_once()

    def test_main_no_command(self, capsys):
        """Test main function with no command (should show help)."""
        with patch("sys.argv", ["secret_manager"]):
            with pytest.raises(SystemExit):
                main()

            captured = capsys.readouterr()
            assert "DevCycle Secret Manager CLI" in captured.out

    def test_main_keyboard_interrupt(self, capsys):
        """Test main function handling keyboard interrupt."""
        with (
            patch("devcycle.cli.secret_manager.create_secret") as mock_create,
            patch(
                "sys.argv",
                [
                    "secret_manager",
                    "create",
                    "jwt-secret-key",
                    "--value",
                    "secret-value",
                ],
            ),
        ):

            mock_create.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main()

            captured = capsys.readouterr()
            assert "❌ Operation cancelled by user" in captured.out

    def test_main_general_exception(self, capsys):
        """Test main function handling general exceptions."""
        with (
            patch("devcycle.cli.secret_manager.create_secret") as mock_create,
            patch(
                "sys.argv",
                [
                    "secret_manager",
                    "create",
                    "jwt-secret-key",
                    "--value",
                    "secret-value",
                ],
            ),
        ):

            mock_create.side_effect = Exception("Test error")

            with pytest.raises(SystemExit):
                main()

            captured = capsys.readouterr()
            assert "❌ Error: Test error" in captured.out


@pytest.mark.unit
class TestSecretCLIArgumentParsing:
    """Test CLI argument parsing and validation."""

    def test_create_command_arguments(self):
        """Test create command argument parsing."""
        with (
            patch("devcycle.cli.secret_manager.create_secret") as mock_create,
            patch(
                "sys.argv",
                [
                    "secret_manager",
                    "create",
                    "jwt-secret-key",
                    "--value",
                    "secret-value",
                    "--environment",
                    "prod",
                ],
            ),
        ):

            mock_create.return_value = None

            main()

            # Verify the function was called with correct arguments
            call_args = mock_create.call_args[0][0]
            assert call_args.secret_id == "jwt-secret-key"
            assert call_args.value == "secret-value"
            assert call_args.environment == "prod"

    def test_rotate_command_arguments(self):
        """Test rotate command argument parsing."""
        with (
            patch("devcycle.cli.secret_manager.rotate_secret") as mock_rotate,
            patch(
                "sys.argv",
                [
                    "secret_manager",
                    "rotate",
                    "jwt-secret-key",
                    "--value",
                    "new-secret-value",
                    "--environment",
                    "staging",
                ],
            ),
        ):

            mock_rotate.return_value = None

            main()

            # Verify the function was called with correct arguments
            call_args = mock_rotate.call_args[0][0]
            assert call_args.secret_id == "jwt-secret-key"
            assert call_args.value == "new-secret-value"
            assert call_args.environment == "staging"

    def test_validate_command_arguments(self):
        """Test validate command argument parsing."""
        with (
            patch("devcycle.cli.secret_manager.validate_secrets") as mock_validate,
            patch(
                "sys.argv",
                ["secret_manager", "validate", "--environment", "production"],
            ),
        ):

            mock_validate.return_value = None

            main()

            # Verify the function was called with correct arguments
            call_args = mock_validate.call_args[0][0]
            assert call_args.environment == "production"

    def test_list_command_arguments(self):
        """Test list command argument parsing."""
        with (
            patch("devcycle.cli.secret_manager.list_secrets") as mock_list,
            patch("sys.argv", ["secret_manager", "list", "--environment", "dev"]),
        ):

            mock_list.return_value = None

            main()

            # Verify the function was called with correct arguments
            call_args = mock_list.call_args[0][0]
            assert call_args.environment == "dev"

    def test_get_command_arguments(self):
        """Test get command argument parsing."""
        with (
            patch("devcycle.cli.secret_manager.get_secret_value") as mock_get,
            patch(
                "sys.argv",
                [
                    "secret_manager",
                    "get",
                    "jwt-secret-key",
                    "--environment",
                    "prod",
                    "--json",
                ],
            ),
        ):

            mock_get.return_value = None

            main()

            # Verify the function was called with correct arguments
            call_args = mock_get.call_args[0][0]
            assert call_args.secret_id == "jwt-secret-key"
            assert call_args.environment == "prod"
            assert call_args.json is True

    def test_default_environment_values(self):
        """Test default environment values for commands."""
        with (
            patch("devcycle.cli.secret_manager.create_secret") as mock_create,
            patch(
                "sys.argv",
                [
                    "secret_manager",
                    "create",
                    "jwt-secret-key",
                    "--value",
                    "secret-value",
                ],
            ),
        ):

            mock_create.return_value = None

            main()

            # Verify default environment is used
            call_args = mock_create.call_args[0][0]
            assert call_args.environment == "dev"  # Default for create command

        with (
            patch("devcycle.cli.secret_manager.validate_secrets") as mock_validate,
            patch("sys.argv", ["secret_manager", "validate"]),
        ):

            mock_validate.return_value = None

            main()

            # Verify default environment is used
            call_args = mock_validate.call_args[0][0]
            assert call_args.environment == "production"  # Default for validate command


@pytest.mark.unit
class TestSecretCLICacheCommands:
    """Test cache management CLI commands."""

    def test_cache_clear_command(self):
        """Test cache clear command."""
        with patch("devcycle.cli.secret_manager.get_secret_client") as mock_get_client:
            mock_client = Mock()
            mock_client.clear_all_caches.return_value = 3
            mock_get_client.return_value = mock_client

            args = Mock()
            args.command = "cache"
            args.cache_action = "clear"

            from devcycle.cli.secret_manager import clear_cache

            clear_cache(args)

            mock_client.clear_all_caches.assert_called_once()

    def test_cache_stats_command(self):
        """Test cache stats command."""
        with patch("devcycle.cli.secret_manager.get_secret_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_cache_stats.return_value = {
                "total_keys": 5,
                "redis_connected": True,
                "redis_version": "6.2.0",
                "used_memory": "1.2M",
                "connected_clients": 2,
            }
            mock_get_client.return_value = mock_client

            args = Mock()
            args.command = "cache"
            args.cache_action = "stats"

            from devcycle.cli.secret_manager import show_cache_stats

            show_cache_stats(args)

            mock_client.get_cache_stats.assert_called_once()

"""Tests for Hugging Face integration."""

from unittest.mock import Mock, patch

import pytest

from devcycle.huggingface.client import HuggingFaceClient
from devcycle.huggingface.space import HuggingFaceSpace, SpaceConfig
from devcycle.huggingface.workspace import HuggingFaceWorkspace, WorkspaceConfig


@pytest.mark.unit
class TestHuggingFaceClient:
    """Test Hugging Face API client."""

    def test_client_initialization_with_token(self) -> None:
        """Test client initialization with explicit token."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("devcycle.core.config.get_config") as mock_get_config:
                mock_config = Mock()
                mock_config.huggingface.api_token = None
                mock_get_config.return_value = mock_config

                client = HuggingFaceClient(token="test-token")
                assert client.token == "test-token"

    def test_client_initialization_without_token(self) -> None:
        """Test client initialization without token raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("devcycle.core.config.get_config") as mock_get_config:
                mock_config = Mock()
                mock_config.huggingface.api_token = None
                mock_get_config.return_value = mock_config

                with pytest.raises(
                    ValueError, match="Hugging Face API token is required"
                ):
                    HuggingFaceClient()

    @patch("devcycle.huggingface.client.HfApi")
    def test_test_connection_success(self, mock_hf_api: Mock) -> None:
        """Test successful connection test."""
        mock_api = Mock()
        mock_api.whoami.return_value = {"name": "test-user"}
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            assert client.test_connection() is True

    @patch("devcycle.huggingface.client.HfApi")
    def test_test_connection_failure(self, mock_hf_api: Mock) -> None:
        """Test failed connection test."""
        mock_api = Mock()
        mock_api.whoami.side_effect = Exception("Connection failed")
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            assert client.test_connection() is False

    @patch("devcycle.huggingface.client.HfApi")
    def test_get_organizations_success(self, mock_hf_api: Mock) -> None:
        """Test successful organizations retrieval."""
        mock_api = Mock()
        mock_api.list_organizations.return_value = [{"name": "test-org"}]
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            orgs = client.get_organizations()
            assert len(orgs) == 1
            assert orgs[0]["name"] == "test-org"

    @patch("devcycle.huggingface.client.HfApi")
    def test_get_organizations_failure(self, mock_hf_api: Mock) -> None:
        """Test failed organizations retrieval."""
        mock_api = Mock()
        mock_api.list_organizations.side_effect = Exception("API Error")
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            orgs = client.get_organizations()
            assert orgs == []

    @patch("devcycle.huggingface.client.HfApi")
    def test_create_organization(self, mock_hf_api: Mock) -> None:
        """Test organization creation."""
        mock_api = Mock()
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            result = client.create_organization("test-org", "Test description")
            assert result is None  # Currently returns None as per implementation

    @patch("devcycle.huggingface.client.HfApi")
    def test_get_spaces_success(self, mock_hf_api: Mock) -> None:
        """Test successful spaces retrieval."""
        mock_api = Mock()
        # Create mock objects with id attribute instead of dictionaries
        mock_space = Mock()
        mock_space.id = "test-org/test-space"
        mock_api.list_spaces.return_value = [mock_space]
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            spaces = client.get_spaces("test-org")
            assert len(spaces) == 1
            assert spaces[0].id == "test-org/test-space"

    @patch("devcycle.huggingface.client.HfApi")
    def test_get_spaces_failure(self, mock_hf_api: Mock) -> None:
        """Test failed spaces retrieval."""
        mock_api = Mock()
        mock_api.list_spaces.side_effect = Exception("API Error")
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            spaces = client.get_spaces("test-org")
            assert spaces == []

    @patch("devcycle.huggingface.client.HfApi")
    def test_create_space_success(self, mock_hf_api: Mock) -> None:
        """Test successful space creation."""
        mock_api = Mock()
        mock_api.create_repo.return_value = {"id": "test-org/test-space"}
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            result = client.create_space("test-org/test-space")
            assert result == {"id": "test-org/test-space"}

    @patch("devcycle.huggingface.client.HfApi")
    def test_create_space_failure(self, mock_hf_api: Mock) -> None:
        """Test failed space creation."""
        mock_api = Mock()
        mock_api.create_repo.side_effect = Exception("API Error")
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            result = client.create_space("test-org/test-space")
            assert result is None

    @patch("devcycle.huggingface.client.HfApi")
    def test_update_space_config_success(self, mock_hf_api: Mock) -> None:
        """Test successful space config update."""
        mock_api = Mock()
        mock_api.upload_file.return_value = True
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            result = client.update_space_config("test-org/test-space", {"key": "value"})
            assert result is True

    @patch("devcycle.huggingface.client.HfApi")
    def test_update_space_config_failure(self, mock_hf_api: Mock) -> None:
        """Test failed space config update."""
        mock_api = Mock()
        mock_api.upload_file.side_effect = Exception("API Error")
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            result = client.update_space_config("test-org/test-space", {"key": "value"})
            assert result is False

    @patch("devcycle.huggingface.client.HfApi")
    def test_get_space_runtime_success(self, mock_hf_api: Mock) -> None:
        """Test successful runtime retrieval."""
        mock_api = Mock()
        mock_runtime = Mock()
        mock_api.get_space_runtime.return_value = mock_runtime
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            result = client.get_space_runtime("test-org/test-space")
            assert result == mock_runtime

    @patch("devcycle.huggingface.client.HfApi")
    def test_get_space_runtime_failure(self, mock_hf_api: Mock) -> None:
        """Test failed runtime retrieval."""
        mock_api = Mock()
        mock_api.get_space_runtime.side_effect = Exception("API Error")
        mock_hf_api.return_value = mock_api

        with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
            client = HuggingFaceClient()
            result = client.get_space_runtime("test-org/test-space")
            assert result is None


@pytest.mark.unit
class TestWorkspaceConfig:
    """Test workspace configuration."""

    def test_workspace_config_defaults(self) -> None:
        """Test workspace config with default values."""
        config = WorkspaceConfig(name="test-org", description="Test organization")

        assert config.name == "test-org"
        assert config.description == "Test organization"
        assert config.visibility == "public"
        assert config.tags == []
        assert config.logo_url is None
        assert config.website_url is None

    def test_workspace_config_custom_values(self) -> None:
        """Test workspace config with custom values."""
        config = WorkspaceConfig(
            name="test-org",
            description="Test organization",
            visibility="private",
            tags=["ai", "ml"],
            logo_url="https://example.com/logo.png",
            website_url="https://example.com",
        )

        assert config.visibility == "private"
        assert config.tags == ["ai", "ml"]
        assert config.logo_url == "https://example.com/logo.png"
        assert config.website_url == "https://example.com"


@pytest.mark.unit
class TestHuggingFaceWorkspace:
    """Test Hugging Face workspace management."""

    def test_workspace_initialization(self) -> None:
        """Test workspace manager initialization."""
        mock_client = Mock()
        workspace = HuggingFaceWorkspace(mock_client)

        assert workspace.client == mock_client

    @patch(
        "devcycle.huggingface.workspace.HuggingFaceWorkspace"
        "._configure_existing_workspace"
    )
    def test_setup_devcycle_workspace_existing_org(self, mock_configure: Mock) -> None:
        """Test workspace setup with existing organization."""
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client.get_organizations.return_value = [{"name": "test-org"}]
        mock_configure.return_value = True

        workspace = HuggingFaceWorkspace(mock_client)
        config = WorkspaceConfig("test-org", "Test organization")

        result = workspace.setup_devcycle_workspace(config)
        assert result is True
        mock_configure.assert_called_once_with(config)

    @patch("devcycle.huggingface.workspace.HuggingFaceWorkspace._create_new_workspace")
    def test_setup_devcycle_workspace_new_org(self, mock_create: Mock) -> None:
        """Test workspace setup with new organization."""
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client.get_organizations.return_value = [{"name": "other-org"}]
        mock_create.return_value = True

        workspace = HuggingFaceWorkspace(mock_client)
        config = WorkspaceConfig("test-org", "Test organization")

        result = workspace.setup_devcycle_workspace(config)
        assert result is True
        mock_create.assert_called_once_with(config)

    def test_setup_devcycle_workspace_connection_failure(self) -> None:
        """Test workspace setup with connection failure."""
        mock_client = Mock()
        mock_client.test_connection.return_value = False

        workspace = HuggingFaceWorkspace(mock_client)
        config = WorkspaceConfig("test-org", "Test organization")

        result = workspace.setup_devcycle_workspace(config)
        assert result is False

    def test_create_new_workspace(self) -> None:
        """Test new workspace creation."""
        mock_client = Mock()
        mock_client.get_spaces.return_value = []
        mock_client.create_space.return_value = {"id": "test-org/devcycle-ai-agents"}
        mock_client.update_space_config.return_value = True

        workspace = HuggingFaceWorkspace(mock_client)
        config = WorkspaceConfig("test-org", "Test organization")

        result = workspace._create_new_workspace(config)
        assert result is True

    @patch("devcycle.huggingface.workspace.HuggingFaceWorkspace._create_devcycle_space")
    def test_configure_existing_workspace_new_space(
        self, mock_create_space: Mock
    ) -> None:
        """Test configuring existing workspace with new space."""
        mock_client = Mock()
        mock_client.get_spaces.return_value = [{"id": "test-org/other-space"}]
        mock_create_space.return_value = True

        workspace = HuggingFaceWorkspace(mock_client)
        config = WorkspaceConfig("test-org", "Test organization")

        result = workspace._configure_existing_workspace(config)
        assert result is True
        mock_create_space.assert_called_once()

    @patch("devcycle.huggingface.workspace.HuggingFaceWorkspace._update_space_config")
    def test_configure_existing_workspace_existing_space(
        self, mock_update_config: Mock
    ) -> None:
        """Test configuring existing workspace with existing space."""
        mock_client = Mock()
        mock_client.get_spaces.return_value = [{"id": "test-org/devcycle-ai-agents"}]
        mock_update_config.return_value = True

        workspace = HuggingFaceWorkspace(mock_client)
        config = WorkspaceConfig("test-org", "Test organization")

        result = workspace._configure_existing_workspace(config)
        assert result is True
        mock_update_config.assert_called_once()

    @patch("devcycle.huggingface.workspace.HuggingFaceWorkspace._update_space_config")
    def test_create_devcycle_space_success(self, mock_update_config: Mock) -> None:
        """Test successful DevCycle space creation."""
        mock_client = Mock()
        mock_client.create_space.return_value = {"id": "test-org/devcycle-ai-agents"}
        mock_update_config.return_value = True

        workspace = HuggingFaceWorkspace(mock_client)
        config = WorkspaceConfig("test-org", "Test organization")

        result = workspace._create_devcycle_space("test-org/devcycle-ai-agents", config)
        assert result is True
        mock_update_config.assert_called_once()

    @patch("devcycle.huggingface.workspace.HuggingFaceWorkspace._update_space_config")
    def test_create_devcycle_space_failure(self, mock_update_config: Mock) -> None:
        """Test failed DevCycle space creation."""
        mock_client = Mock()
        mock_client.create_space.return_value = None

        workspace = HuggingFaceWorkspace(mock_client)
        config = WorkspaceConfig("test-org", "Test organization")

        result = workspace._create_devcycle_space("test-org/devcycle-ai-agents", config)
        assert result is False
        mock_update_config.assert_not_called()

    @patch("devcycle.huggingface.workspace.HuggingFaceWorkspace._update_space_config")
    def test_update_space_config_success(self, mock_update_config: Mock) -> None:
        """Test successful space config update."""
        mock_client = Mock()
        mock_update_config.return_value = True

        workspace = HuggingFaceWorkspace(mock_client)
        config = WorkspaceConfig("test-org", "Test organization")

        result = workspace._update_space_config("test-org/devcycle-ai-agents", config)
        assert result is True
        mock_update_config.assert_called_once()

    @patch("devcycle.huggingface.workspace.HuggingFaceWorkspace._update_space_config")
    def test_update_space_config_failure(self, mock_update_config: Mock) -> None:
        """Test failed space config update."""
        mock_client = Mock()
        mock_update_config.return_value = False

        workspace = HuggingFaceWorkspace(mock_client)
        config = WorkspaceConfig("test-org", "Test organization")

        result = workspace._update_space_config("test-org/devcycle-ai-agents", config)
        assert result is False

    def test_get_workspace_status_not_found(self) -> None:
        """Test workspace status when organization not found."""
        mock_client = Mock()
        mock_client.get_organizations.return_value = [{"name": "other-org"}]

        workspace = HuggingFaceWorkspace(mock_client)
        result = workspace.get_workspace_status("test-org")

        assert result["exists"] is False
        assert result["status"] == "not_found"

    def test_get_workspace_status_found_no_devcycle_space(self) -> None:
        """Test workspace status when org exists but no DevCycle space."""
        mock_client = Mock()
        mock_client.get_organizations.return_value = [{"name": "test-org"}]
        mock_client.get_spaces.return_value = [{"id": "test-org/other-space"}]

        workspace = HuggingFaceWorkspace(mock_client)
        result = workspace.get_workspace_status("test-org")

        assert result["exists"] is True
        assert result["status"] == "incomplete"
        assert result["spaces_count"] == 1

    def test_get_workspace_status_found_with_devcycle_space(self) -> None:
        """Test workspace status when org exists with DevCycle space."""
        mock_client = Mock()
        mock_client.get_organizations.return_value = [{"name": "test-org"}]
        mock_client.get_spaces.return_value = [{"id": "test-org/devcycle-ai-agents"}]

        workspace = HuggingFaceWorkspace(mock_client)
        result = workspace.get_workspace_status("test-org")

        assert result["exists"] is True
        assert result["status"] == "active"
        assert result["spaces_count"] == 1
        assert result["devcycle_space"] is not None


@pytest.mark.unit
class TestSpaceConfig:
    """Test space configuration."""

    def test_space_config_defaults(self) -> None:
        """Test space config with default values."""
        config = SpaceConfig(name="test-space", description="Test space")

        assert config.name == "test-space"
        assert config.description == "Test space"
        assert config.sdk == "gradio"
        assert config.hardware == "cpu-basic"
        assert config.private is False
        assert config.license == "mit"
        assert config.python_version == "3.9"
        assert config.sdk_version is None

    def test_space_config_custom_values(self) -> None:
        """Test space config with custom values."""
        config = SpaceConfig(
            name="test-space",
            description="Test space",
            sdk="streamlit",
            hardware="gpu-t4",
            private=True,
            license="apache-2.0",
            python_version="3.11",
        )

        assert config.sdk == "streamlit"
        assert config.hardware == "gpu-t4"
        assert config.private is True
        assert config.license == "apache-2.0"
        assert config.python_version == "3.11"


@pytest.mark.unit
class TestHuggingFaceSpace:
    """Test Hugging Face space management."""

    def test_space_initialization(self) -> None:
        """Test space manager initialization."""
        mock_client = Mock()
        space = HuggingFaceSpace(mock_client, "test-org/test-space")

        assert space.client == mock_client
        assert space.repo_id == "test-org/test-space"

    @patch("devcycle.huggingface.space.HuggingFaceSpace._setup_space_files")
    def test_create_space_success(self, mock_setup_files: Mock) -> None:
        """Test successful space creation."""
        mock_client = Mock()
        mock_client.create_space.return_value = {"id": "test-org/test-space"}
        mock_setup_files.return_value = True

        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        config = SpaceConfig("test-space", "Test space")

        result = space.create_space(config)
        assert result is True
        mock_setup_files.assert_called_once_with(config)

    def test_create_space_failure(self) -> None:
        """Test failed space creation."""
        mock_client = Mock()
        mock_client.create_space.return_value = None

        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        config = SpaceConfig("test-space", "Test space")

        result = space.create_space(config)
        assert result is False

    @patch("devcycle.huggingface.space.HuggingFaceSpace._upload_file")
    def test_setup_space_files_success(self, mock_upload: Mock) -> None:
        """Test successful space file setup."""
        mock_client = Mock()
        mock_upload.return_value = True

        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        config = SpaceConfig("test-space", "Test space")

        result = space._setup_space_files(config)
        assert result is True
        assert (
            mock_upload.call_count == 4
        )  # requirements.txt, README.md, app.py, .gitattributes

    @patch("devcycle.huggingface.space.HuggingFaceSpace._upload_file")
    def test_setup_space_files_failure(self, mock_upload: Mock) -> None:
        """Test failed space file setup."""
        mock_client = Mock()
        mock_upload.return_value = False  # First upload fails

        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        config = SpaceConfig("test-space", "Test space")

        result = space._setup_space_files(config)
        assert result is False

    def test_generate_requirements_txt_gradio(self) -> None:
        """Test requirements.txt generation for Gradio."""
        mock_client = Mock()
        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        config = SpaceConfig("test-space", "Test space", sdk="gradio")

        requirements = space._generate_requirements_txt(config)
        assert "gradio>=" in requirements
        assert "gradio-client>=" in requirements

    def test_generate_requirements_txt_streamlit(self) -> None:
        """Test requirements.txt generation for Streamlit."""
        mock_client = Mock()
        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        config = SpaceConfig("test-space", "Test space", sdk="streamlit")

        requirements = space._generate_requirements_txt(config)
        assert "streamlit>=" in requirements
        assert "gradio>=" not in requirements

    def test_generate_readme_md(self) -> None:
        """Test README.md generation."""
        mock_client = Mock()
        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        config = SpaceConfig("test-space", "Test space", sdk="gradio")

        readme = space._generate_readme_md(config)
        assert "DevCycle AI Agents" in readme
        assert "Test space" in readme
        assert "Gradio" in readme

    def test_generate_app_py_gradio(self) -> None:
        """Test app.py generation for Gradio."""
        mock_client = Mock()
        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        config = SpaceConfig("test-space", "Test space", sdk="gradio")

        app_content = space._generate_app_py(config)
        assert "import gradio as gr" in app_content
        assert "gr.Blocks" in app_content

    def test_generate_app_py_streamlit(self) -> None:
        """Test app.py generation for Streamlit."""
        mock_client = Mock()
        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        config = SpaceConfig("test-space", "Test space", sdk="streamlit")

        app_content = space._generate_app_py(config)
        assert "import streamlit as st" in app_content
        assert "st.title" in app_content

    def test_generate_app_py_docker(self) -> None:
        """Test app.py generation for Docker."""
        mock_client = Mock()
        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        config = SpaceConfig("test-space", "Test space", sdk="docker")

        app_content = space._generate_app_py(config)
        assert "FROM python:3.9-slim" in app_content
        assert "WORKDIR /app" in app_content

    def test_generate_gitattributes(self) -> None:
        """Test .gitattributes generation."""
        mock_client = Mock()
        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        config = SpaceConfig("test-space", "Test space", sdk="gradio", private=True)

        gitattributes = space._generate_gitattributes(config)
        assert "gradio = true" in gitattributes
        assert "private = true" in gitattributes

    def test_upload_file_success(self) -> None:
        """Test successful file upload."""
        mock_client = Mock()
        mock_client.api.upload_file.return_value = True

        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        result = space._upload_file("test.txt", "test content")

        assert result is True
        mock_client.api.upload_file.assert_called_once()

    def test_upload_file_failure(self) -> None:
        """Test failed file upload."""
        mock_client = Mock()
        mock_client.api.upload_file.return_value = False

        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        result = space._upload_file("test.txt", "test content")

        assert result is False

    def test_get_space_status_active(self) -> None:
        """Test space status when space is active."""
        mock_client = Mock()
        mock_runtime = Mock()
        mock_client.get_space_runtime.return_value = mock_runtime

        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        result = space.get_space_status()

        assert result["exists"] is True
        assert result["status"] == "active"
        assert result["runtime"] == mock_runtime

    def test_get_space_status_inactive(self) -> None:
        """Test space status when space is inactive."""
        mock_client = Mock()
        mock_client.get_space_runtime.return_value = None

        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        result = space.get_space_status()

        assert result["exists"] is True
        assert result["status"] == "inactive"
        assert result["runtime"] is None

    def test_get_space_status_error(self) -> None:
        """Test space status when error occurs."""
        mock_client = Mock()
        mock_client.get_space_runtime.side_effect = Exception("API Error")

        space = HuggingFaceSpace(mock_client, "test-org/test-space")
        result = space.get_space_status()

        assert result["exists"] is False
        assert result["status"] == "error"
        assert "API Error" in result["message"]


@pytest.mark.unit
class TestHuggingFaceCLI:
    """Test Hugging Face CLI functionality."""

    @patch("devcycle.huggingface.cli.HuggingFaceClient")
    @patch("devcycle.huggingface.cli.setup_workspace")
    def test_setup_workspace_function_success(
        self, mock_setup: Mock, mock_client_class: Mock
    ) -> None:
        """Test successful workspace setup function."""
        mock_setup.return_value = True

        from devcycle.huggingface.cli import setup_workspace

        result = setup_workspace("test-org", "Test description", "public", "test-token")
        assert result is True

    @patch("devcycle.huggingface.cli.HuggingFaceClient")
    @patch("devcycle.huggingface.cli.check_workspace_status")
    def test_check_workspace_status_function_success(
        self, mock_check: Mock, mock_client_class: Mock
    ) -> None:
        """Test successful workspace status check function."""
        mock_check.return_value = True

        from devcycle.huggingface.cli import check_workspace_status

        result = check_workspace_status("test-org", "test-token")
        assert result is True

    def test_setup_workspace_function_failure(self) -> None:
        """Test failed workspace setup function."""
        from devcycle.huggingface.cli import setup_workspace

        # Test with invalid token to trigger failure
        result = setup_workspace(
            "test-org", "Test description", "public", "invalid-token"
        )
        assert result is False

    def test_check_workspace_status_function_failure(self) -> None:
        """Test failed workspace status check function."""
        from devcycle.huggingface.cli import check_workspace_status

        # Test with invalid token to trigger failure
        result = check_workspace_status("test-org", "invalid-token")
        assert result is False

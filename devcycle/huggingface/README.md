# Hugging Face Integration

This module provides integration with Hugging Face for hosting DevCycle AI agents as Spaces.

## Overview

The Hugging Face integration allows DevCycle to:
- Create and manage Hugging Face workspaces
- Deploy AI agents as interactive web applications
- Manage space configurations and deployments
- Provide a unified interface for agent hosting

## Architecture

### Single Space Approach

DevCycle uses a **single Hugging Face Space** that hosts all AI agents:
- **Requirements Agent**: Analyzes software requirements
- **Code Generation Agent**: Generates code based on requirements
- **Testing Agent**: Creates and runs tests
- **Deployment Agent**: Manages deployment orchestration

This approach provides:
- Simpler management and deployment
- Unified user interface
- Easier agent coordination
- Reduced complexity for the POC phase

## Components

### 1. HuggingFaceClient

Core API client for interacting with Hugging Face:
- Authentication and connection management
- Organization and space operations
- File uploads and configuration updates

### 2. HuggingFaceWorkspace

Manages workspace-level operations:
- Organization setup and configuration
- Workspace branding and metadata
- User permission management

### 3. HuggingFaceSpace

Handles individual space management:
- Space creation and configuration
- File generation and uploads
- Runtime status monitoring

### 4. CLI Interface

Command-line tools for workspace management:
- `setup`: Create and configure DevCycle workspace
- `status`: Check workspace and space status

## Usage

### Basic Setup

```python
from devcycle.huggingface import setup_workspace

# Setup DevCycle workspace
success = setup_workspace(
    org_name="devcycle",
    description="AI-Powered Development Lifecycle Automation",
    visibility="public"
)
```

### Advanced Usage

```python
from devcycle.huggingface import (
    HuggingFaceClient,
    HuggingFaceWorkspace,
    WorkspaceConfig
)

# Initialize client
client = HuggingFaceClient(token="your-hf-token")

# Create workspace configuration
config = WorkspaceConfig(
    name="devcycle",
    description="AI-Powered Development Lifecycle Automation",
    visibility="public",
    tags=["ai", "agents", "development"]
)

# Setup workspace
workspace = HuggingFaceWorkspace(client)
success = workspace.setup_devcycle_workspace(config)
```

### CLI Usage

```bash
# Setup workspace
python -m devcycle.huggingface.cli setup devcycle "AI-Powered Development Lifecycle Automation"

# Check status
python -m devcycle.huggingface.cli status devcycle
```

## Configuration

### Environment Variables

- `HF_TOKEN`: Hugging Face API token (required)

### Workspace Configuration

- **Name**: Organization name on Hugging Face
- **Description**: Workspace description and purpose
- **Visibility**: Public or private workspace
- **Tags**: Keywords for discovery and categorization

### Space Configuration

- **SDK**: Gradio (default), Streamlit, or Docker
- **Hardware**: CPU or GPU configuration
- **License**: MIT (default) or other open source licenses
- **Python Version**: Python 3.9+ compatibility

## Generated Files

When creating a space, the following files are automatically generated:

### requirements.txt
Dependencies for the space application:
- Gradio/Streamlit for web interface
- Transformers for AI models
- PyTorch for machine learning
- Other utility libraries

### app.py
Main application file with:
- Interactive web interface
- Agent selection and configuration
- Input/output handling
- Error handling and logging

### README.md
Space documentation including:
- Feature descriptions
- Usage instructions
- Technology stack
- Development information

### .gitattributes
Space configuration for:
- SDK specification
- Hardware requirements
- Python version
- License and visibility

## Testing

Run the test suite:

```bash
# Run all Hugging Face tests
pytest tests/test_huggingface.py -v

# Run with coverage
pytest tests/test_huggingface.py --cov=devcycle.huggingface -v
```

## Examples

See `examples/huggingface_workspace_setup.py` for a complete example of:
- Workspace setup
- Space creation
- Configuration management
- Status monitoring

## Next Steps

After workspace setup, the next phases include:
1. **Agent Implementation**: Develop the actual AI agent logic
2. **Model Integration**: Integrate with Hugging Face models
3. **API Development**: Create REST APIs for agent communication
4. **Orchestration**: Implement workflow coordination between agents

## Troubleshooting

### Common Issues

1. **Authentication Error**: Ensure `HF_TOKEN` is set correctly
2. **Permission Denied**: Check organization access and permissions
3. **Space Creation Failed**: Verify organization exists and has space creation rights
4. **File Upload Errors**: Check network connectivity and API limits

### Debug Mode

Enable debug logging for detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When contributing to the Hugging Face integration:

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new functionality
3. Update documentation for new features
4. Ensure error handling and logging are robust
5. Test with both public and private workspaces

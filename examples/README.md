# DevCycle Examples

This directory contains example scripts that demonstrate various aspects of the DevCycle system.

## Available Examples

### 1. `business_analyst_demo.py`
**Purpose**: Demonstrates the Business Analyst Agent capabilities

**What it shows**:
- Creating and initializing a Business Analyst Agent
- Processing different types of business requirements (string, structured, bug reports)
- Agent status and execution history
- Requirements summary and statistics

**Usage**:
```bash
poetry run python examples/business_analyst_demo.py
```

**Key Features Demonstrated**:
- Agent initialization and configuration
- Requirement processing with different input formats
- Agent status monitoring
- Requirements tracking and summarization

### 2. `message_protocol_demo.py`
**Purpose**: Demonstrates the message protocol for agent communication

**What it shows**:
- Creating command messages (System → Agent)
- Creating event messages (Agent → System)
- Message serialization and structure
- Complete workflow example (business analysis)

**Usage**:
```bash
poetry run python examples/message_protocol_demo.py
```

**Key Features Demonstrated**:
- Message protocol structure
- Command and event message types
- Progress tracking through messages
- Structured data exchange between system and agents

### 3. `kafka_messaging_demo.py`
**Purpose**: Demonstrates Kafka-based message queue implementation

**What it shows**:
- Setting up Kafka message queue
- Sending and receiving messages
- Message priority handling
- Performance testing

**Usage**:
```bash
# Requires Kafka to be running
poetry run python examples/kafka_messaging_demo.py
```

**Prerequisites**:
- Kafka server running on `localhost:9092`
- Kafka topics configured

**Key Features Demonstrated**:
- Kafka queue initialization
- Message publishing and consumption
- Priority-based message handling
- Performance metrics

### 4. `huggingface_workspace_setup.py`
**Purpose**: Demonstrates Hugging Face workspace integration

**What it shows**:
- Connecting to Hugging Face API
- Creating and configuring workspaces
- Workspace status checking
- Organization management

**Usage**:
```bash
# Requires Hugging Face API token
export HF_TOKEN="your-token-here"
poetry run python examples/huggingface_workspace_setup.py
```

**Prerequisites**:
- Hugging Face API token
- Valid Hugging Face account

**Key Features Demonstrated**:
- Hugging Face API integration
- Workspace creation and management
- Organization handling
- Status monitoring

### 5. `api_client_demo.py`
**Purpose**: Demonstrates API client usage and interaction patterns

**What it shows**:
- API client implementation
- Authentication flow
- Health check endpoints
- Agent and message operations
- Error handling patterns

**Usage**:
```bash
# Requires API server to be running
poetry run uvicorn devcycle.api.app:app --reload
# In another terminal:
poetry run python examples/api_client_demo.py
```

**Prerequisites**:
- DevCycle API server running on `localhost:8000`
- Valid user credentials (for authentication demo)

**Key Features Demonstrated**:
- HTTP client implementation
- JWT authentication
- RESTful API interaction
- Error handling and status codes
- API versioning

## Running Examples

### Prerequisites
1. **Install dependencies**:
   ```bash
   poetry install
   ```

2. **Set up environment** (if needed):
   ```bash
   # For Hugging Face examples
   export HF_TOKEN="your-huggingface-token"

   # For Kafka examples
   # Start Kafka server on localhost:9092
   ```

### Basic Examples (No External Dependencies)
These examples work out of the box:
- `business_analyst_demo.py`
- `message_protocol_demo.py`

### API Examples
For API examples, start the server first:
```bash
poetry run uvicorn devcycle.api.app:app --reload
```

### External Service Examples
For examples requiring external services:
- **Kafka**: Start Kafka server
- **Hugging Face**: Set up API token

## Example Outputs

### Business Analyst Demo
```
🚀 Business Analyst Agent Demo
==================================================
✅ Created agent: demo_analyst

📝 Demo 1: Simple String Requirement
----------------------------------------
✅ Processed requirement: Business Requirement
📊 Priority: medium
🏷️  Category: feature
💡 Recommendations: 2
```

### Message Protocol Demo
```
🚀 DevCycle Message Protocol Demo
==================================================

📤 Step 1: System → Business Analyst Agent
----------------------------------------
Command Message:
{
  "header": {
    "message_id": "ce981009-2347-4b9f-ab85-d6edcd78a21b",
    "timestamp": "2025-09-01T23:05:06.983167+00:00",
    "agent_id": "business_analyst",
    "message_type": "command",
    "version": "1.0"
  },
  "body": {
    "action": "analyze_business_requirement",
    "data": { ... }
  }
}
```

## Integration with Documentation

These examples complement the main API documentation:

- **API Documentation**: `/docs` (Swagger UI)
- **API Guide**: `docs/api-documentation.md`
- **Examples**: This directory

## Contributing

When adding new examples:

1. **Follow the naming convention**: `{feature}_demo.py`
2. **Include comprehensive docstrings**
3. **Add error handling and logging**
4. **Update this README**
5. **Test with the current codebase**

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the project root
2. **Connection Errors**: Check if required services are running
3. **Authentication Errors**: Verify credentials and tokens
4. **Dependency Errors**: Run `poetry install` to ensure all dependencies are installed

### Getting Help

- Check the main documentation: `docs/api-documentation.md`
- Review the API documentation: `http://localhost:8000/docs`
- Check the test files for additional usage examples

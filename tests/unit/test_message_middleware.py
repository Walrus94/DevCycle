"""
Unit tests for message validation middleware.

This module tests the MessageValidationMiddleware and MessageValidator classes,
ensuring proper request validation and error handling.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from devcycle.core.messaging.middleware import (
    MessageValidationMiddleware,
    MessageValidator,
)
from devcycle.core.messaging.validation import MessageValidationConfig
from devcycle.core.messaging.validation_errors import (
    MessageSizeError,
    MessageValidationError,
)


class TestMessageValidationMiddleware:
    """Test cases for MessageValidationMiddleware."""

    @pytest.fixture
    def config(self):
        """Create a validation config for testing."""
        return MessageValidationConfig(
            max_message_size_bytes=1024 * 1024,  # 1MB
            max_data_size_bytes=512 * 1024,  # 512KB
            enable_warnings=True,
        )

    @pytest.fixture
    def middleware(self, config):
        """Create a middleware instance for testing."""
        return MessageValidationMiddleware(config)

    @pytest.fixture
    def mock_request(self):
        """Create a mock request for testing."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/messages/send"
        request.method = "POST"
        request.headers = {"content-type": "application/json", "content-length": "100"}
        # Set up default body for successful requests
        request.body = AsyncMock(
            return_value=json.dumps(
                {
                    "agent_id": "test_agent",
                    "action": "test_action",
                    "data": {"test": "value"},
                }
            ).encode()
        )
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create a mock call_next function."""

        async def call_next(request):
            return JSONResponse(content={"status": "success"})

        return call_next

    @pytest.mark.asyncio
    async def test_middleware_initialization(self, config):
        """Test middleware initialization."""
        middleware = MessageValidationMiddleware(config)
        assert middleware.config == config

    @pytest.mark.asyncio
    async def test_middleware_successful_request(
        self, middleware, mock_request, mock_call_next
    ):
        """Test middleware with successful request."""
        response = await middleware(mock_request, mock_call_next)

        assert response.status_code == 200
        assert response.body == b'{"status":"success"}'

    @pytest.mark.asyncio
    async def test_middleware_request_size_validation(
        self, middleware, mock_request, mock_call_next
    ):
        """Test middleware request size validation."""
        # Set content length to exceed limit
        mock_request.headers["content-length"] = str(2 * 1024 * 1024)  # 2MB

        with pytest.raises(MessageSizeError) as exc_info:
            await middleware(mock_request, mock_call_next)

        assert exc_info.value.status_code == 413
        assert "size exceeds limit" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_middleware_content_type_validation(
        self, middleware, mock_request, mock_call_next
    ):
        """Test middleware content type validation."""
        # Set invalid content type
        mock_request.headers["content-type"] = "text/plain"

        with pytest.raises(MessageValidationError) as exc_info:
            await middleware(mock_request, mock_call_next)

        assert exc_info.value.status_code == 400
        assert "Invalid content type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_middleware_non_message_endpoint(self, middleware, mock_call_next):
        """Test middleware with non-message endpoint."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/health"
        request.method = "GET"
        request.headers = {}

        response = await middleware(request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_get_request(
        self, middleware, mock_request, mock_call_next
    ):
        """Test middleware with GET request (should skip validation)."""
        mock_request.method = "GET"

        response = await middleware(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_empty_body(
        self, middleware, mock_request, mock_call_next
    ):
        """Test middleware with empty request body."""
        mock_request.body = AsyncMock(return_value=b"")

        response = await middleware(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_invalid_json(
        self, middleware, mock_request, mock_call_next
    ):
        """Test middleware with invalid JSON."""
        mock_request.body = AsyncMock(return_value=b"invalid json")

        with pytest.raises(MessageValidationError) as exc_info:
            await middleware(mock_request, mock_call_next)

        assert exc_info.value.status_code == 400
        assert "Invalid JSON format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_middleware_data_size_validation(
        self, middleware, mock_request, mock_call_next
    ):
        """Test middleware data size validation."""
        # Create large data payload
        large_data = {"data": "x" * (1024 * 1024)}  # 1MB of data
        mock_request.body = AsyncMock(return_value=json.dumps(large_data).encode())

        with pytest.raises(MessageSizeError) as exc_info:
            await middleware(mock_request, mock_call_next)

        assert exc_info.value.status_code == 413
        assert "size exceeds limit" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_middleware_structure_validation_send(
        self, middleware, mock_request, mock_call_next
    ):
        """Test middleware structure validation for send endpoint."""
        valid_data = {
            "agent_id": "test_agent",
            "action": "test_action",
            "data": {"test": "value"},
        }
        mock_request.body = AsyncMock(return_value=json.dumps(valid_data).encode())

        response = await middleware(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_structure_validation_send_missing_fields(
        self, middleware, mock_request, mock_call_next
    ):
        """Test middleware structure validation for send endpoint missing fields."""
        invalid_data = {"action": "test_action"}  # Missing agent_id
        mock_request.body = AsyncMock(return_value=json.dumps(invalid_data).encode())

        with pytest.raises(MessageValidationError) as exc_info:
            await middleware(mock_request, mock_call_next)

        assert exc_info.value.status_code == 400
        assert "Missing required field" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_middleware_structure_validation_broadcast(
        self, middleware, mock_call_next
    ):
        """Test middleware structure validation for broadcast endpoint."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/messages/broadcast"
        request.method = "POST"
        request.headers = {"content-type": "application/json"}

        valid_data = {
            "agent_types": ["business_analyst", "developer"],
            "action": "notify_update",
        }
        request.body = AsyncMock(return_value=json.dumps(valid_data).encode())

        middleware = MessageValidationMiddleware(MessageValidationConfig())
        response = await middleware(request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_structure_validation_route(
        self, middleware, mock_call_next
    ):
        """Test middleware structure validation for route endpoint."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/messages/route"
        request.method = "POST"
        request.headers = {"content-type": "application/json"}

        valid_data = {
            "capabilities": ["text_processing", "analysis"],
            "action": "process_text",
        }
        request.body = AsyncMock(return_value=json.dumps(valid_data).encode())

        middleware = MessageValidationMiddleware(MessageValidationConfig())
        response = await middleware(request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_internal_error_handling(
        self, middleware, mock_request, mock_call_next
    ):
        """Test middleware internal error handling."""

        # Mock call_next to raise an exception
        async def failing_call_next(request):
            raise Exception("Internal server error")

        response = await middleware(mock_request, failing_call_next)

        assert response.status_code == 500
        assert "Internal validation error" in response.body.decode()


class TestMessageValidator:
    """Test cases for MessageValidator."""

    @pytest.fixture
    def config(self):
        """Create a validation config for testing."""
        return MessageValidationConfig(
            max_data_size_bytes=512 * 1024,  # 512KB
            allowed_actions=["action1", "action2"],
            enable_warnings=True,
        )

    @pytest.fixture
    def validator(self, config):
        """Create a validator instance for testing."""
        return MessageValidator(config)

    @pytest.mark.asyncio
    async def test_validator_initialization(self, config):
        """Test validator initialization."""
        validator = MessageValidator(config)
        assert validator.config == config

    @pytest.mark.asyncio
    async def test_validate_message_send_valid(self, validator):
        """Test validating a valid message send request."""
        request_data = {
            "agent_id": "test_agent",
            "action": "action1",
            "data": {"test": "value"},
            "priority": "high",
            "ttl": 3600,
        }

        result = await validator.validate_message_send(request_data)

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    @pytest.mark.asyncio
    async def test_validate_message_send_missing_required_fields(self, validator):
        """Test validating message send request with missing required fields."""
        request_data = {"action": "test_action"}  # Missing agent_id

        result = await validator.validate_message_send(request_data)

        assert result.is_valid is False
        assert "Missing required field: agent_id" in result.errors

    @pytest.mark.asyncio
    async def test_validate_message_send_invalid_field_types(self, validator):
        """Test validating message send request with invalid field types."""
        request_data = {"agent_id": 123, "action": "test_action"}  # Should be string

        result = await validator.validate_message_send(request_data)

        assert result.is_valid is False
        assert "agent_id must be a string" in result.errors

    @pytest.mark.asyncio
    async def test_validate_message_send_field_length_validation(self, validator):
        """Test validating message send request field lengths."""
        request_data = {"agent_id": "", "action": "x" * 300}  # Empty string  # Too long

        result = await validator.validate_message_send(request_data)

        assert result.is_valid is False
        assert "agent_id cannot be empty" in result.errors
        assert "action too long (max 200 characters)" in result.errors

    @pytest.mark.asyncio
    async def test_validate_message_send_invalid_priority(self, validator):
        """Test validating message send request with invalid priority."""
        request_data = {
            "agent_id": "test_agent",
            "action": "test_action",
            "priority": "invalid_priority",
        }

        result = await validator.validate_message_send(request_data)

        assert result.is_valid is False
        assert "Invalid priority: invalid_priority" in result.errors

    @pytest.mark.asyncio
    async def test_validate_message_send_invalid_ttl(self, validator):
        """Test validating message send request with invalid TTL."""
        request_data = {
            "agent_id": "test_agent",
            "action": "test_action",
            "ttl": "not_a_number",
        }

        result = await validator.validate_message_send(request_data)

        assert result.is_valid is False
        assert "ttl must be an integer" in result.errors

    @pytest.mark.asyncio
    async def test_validate_message_send_large_data(self, validator):
        """Test validating message send request with large data."""
        large_data = {"data": "x" * (1024 * 1024)}  # 1MB
        request_data = {
            "agent_id": "test_agent",
            "action": "test_action",
            "data": large_data,
        }

        result = await validator.validate_message_send(request_data)

        assert result.is_valid is False
        assert "Data payload too large:" in result.errors[0]

    @pytest.mark.asyncio
    async def test_validate_message_send_disallowed_action(self, validator):
        """Test validating message send request with disallowed action."""
        request_data = {"agent_id": "test_agent", "action": "disallowed_action"}

        result = await validator.validate_message_send(request_data)

        assert result.is_valid is False
        assert "not allowed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_validate_message_broadcast_valid(self, validator):
        """Test validating a valid message broadcast request."""
        request_data = {
            "agent_types": ["business_analyst", "developer"],
            "action": "notify_update",
            "data": {"update": "value"},
            "exclude_agent_ids": ["agent1", "agent2"],
        }

        result = await validator.validate_message_broadcast(request_data)

        assert result.is_valid is True
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_validate_message_broadcast_missing_fields(self, validator):
        """Test validating message broadcast request with missing fields."""
        request_data = {"action": "test_action"}  # Missing agent_types

        result = await validator.validate_message_broadcast(request_data)

        assert result.is_valid is False
        assert "Missing required field: agent_types" in result.errors

    @pytest.mark.asyncio
    async def test_validate_message_broadcast_invalid_agent_types(self, validator):
        """Test validating message broadcast request with invalid agent types."""
        request_data = {"agent_types": ["invalid_type"], "action": "test_action"}

        result = await validator.validate_message_broadcast(request_data)

        assert result.is_valid is False
        assert "Invalid agent type: invalid_type" in result.errors

    @pytest.mark.asyncio
    async def test_validate_message_broadcast_too_many_agent_types(self, validator):
        """Test validating message broadcast request with too many agent types."""
        agent_types = ["business_analyst"] * 11  # More than max of 10
        request_data = {"agent_types": agent_types, "action": "test_action"}

        result = await validator.validate_message_broadcast(request_data)

        assert result.is_valid is False
        assert "Too many agent types (max 10)" in result.errors

    @pytest.mark.asyncio
    async def test_validate_message_route_valid(self, validator):
        """Test validating a valid message route request."""
        request_data = {
            "capabilities": ["text_processing", "analysis"],
            "action": "process_text",
            "data": {"text": "sample"},
            "load_balancing": "least_busy",
        }

        result = await validator.validate_message_route(request_data)

        assert result.is_valid is True
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_validate_message_route_missing_fields(self, validator):
        """Test validating message route request with missing fields."""
        request_data = {"action": "test_action"}  # Missing capabilities

        result = await validator.validate_message_route(request_data)

        assert result.is_valid is False
        assert "Missing required field: capabilities" in result.errors

    @pytest.mark.asyncio
    async def test_validate_message_route_invalid_capabilities(self, validator):
        """Test validating message route request with invalid capabilities."""
        request_data = {"capabilities": ["invalid_capability"], "action": "test_action"}

        result = await validator.validate_message_route(request_data)

        assert result.is_valid is False
        assert "Invalid capability: invalid_capability" in result.errors

    @pytest.mark.asyncio
    async def test_validate_message_route_invalid_load_balancing(self, validator):
        """Test validating message route request with invalid load balancing."""
        request_data = {
            "capabilities": ["text_processing"],
            "action": "test_action",
            "load_balancing": "invalid_strategy",
        }

        result = await validator.validate_message_route(request_data)

        assert result.is_valid is False
        assert "Invalid load balancing strategy: invalid_strategy" in result.errors

    @pytest.mark.asyncio
    async def test_validation_result_structure(self, validator):
        """Test that validation results have correct structure."""
        request_data = {"agent_id": "test_agent", "action": "test_action"}

        result = await validator.validate_message_send(request_data)

        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    @pytest.mark.asyncio
    async def test_validation_warnings_disabled(self):
        """Test validation with warnings disabled."""
        config = MessageValidationConfig(enable_warnings=False)
        validator = MessageValidator(config)

        request_data = {"agent_id": "test_agent", "action": "test_action"}

        result = await validator.validate_message_send(request_data)

        assert result.is_valid is True
        assert result.warnings == []  # Warnings should be empty when disabled


class TestMessageValidationIntegration:
    """Integration tests for message validation."""

    @pytest.mark.asyncio
    async def test_complete_validation_workflow(self):
        """Test a complete validation workflow."""
        config = MessageValidationConfig(
            max_data_size_bytes=1024 * 1024,  # 1MB
            allowed_actions=["analyze", "process", "notify"],
            enable_warnings=True,
        )

        validator = MessageValidator(config)

        # Test valid send request
        send_data = {
            "agent_id": "business_analyst_1",
            "action": "analyze",
            "data": {"requirement": "Create user management system"},
            "priority": "high",
            "ttl": 3600,
        }

        send_result = await validator.validate_message_send(send_data)
        assert send_result.is_valid is True

        # Test valid broadcast request
        broadcast_data = {
            "agent_types": ["developer", "tester"],
            "action": "notify",
            "data": {"version": "1.0.0"},
        }

        broadcast_result = await validator.validate_message_broadcast(broadcast_data)
        assert broadcast_result.is_valid is True

        # Test valid route request
        route_data = {
            "capabilities": ["text_processing", "analysis"],
            "action": "process",
            "load_balancing": "least_busy",
        }

        route_result = await validator.validate_message_route(route_data)
        assert route_result.is_valid is True

    @pytest.mark.asyncio
    async def test_middleware_validator_integration(self):
        """Test integration between middleware and validator."""
        config = MessageValidationConfig()
        middleware = MessageValidationMiddleware(config)
        validator = MessageValidator(config)

        # Test that both use the same config
        assert middleware.config == validator.config

        # Test validation consistency
        request_data = {"agent_id": "test_agent", "action": "test_action"}

        validator_result = await validator.validate_message_send(request_data)
        assert validator_result.is_valid is True

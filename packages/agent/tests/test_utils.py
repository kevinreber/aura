"""Tests for utility modules."""

import pytest
from unittest.mock import AsyncMock, patch
import asyncio

from daily_ai_agent.utils.error_handlers import (
    APIError,
    MCPError,
    ToolError,
    ValidationError,
    handle_api_error,
    safe_async_call,
)
from daily_ai_agent.utils.async_helpers import (
    run_async,
    gather_with_timeout,
    retry_async,
)
from daily_ai_agent.utils.constants import (
    APP_VERSION,
    FINANCIAL_SYMBOLS,
    SHUTTLE_STOP_NAMES,
    TODO_BUCKETS,
    TRANSPORT_MODES,
)


class TestErrorHandlers:
    """Tests for error handler utilities."""

    def test_api_error_creation(self):
        """Test APIError can be created with all parameters."""
        error = APIError("Test error", status_code=404, details={"field": "test"})
        assert error.message == "Test error"
        assert error.status_code == 404
        assert error.details == {"field": "test"}

    def test_api_error_defaults(self):
        """Test APIError has sensible defaults."""
        error = APIError("Test error")
        assert error.status_code == 500
        assert error.details == {}

    def test_mcp_error_creation(self):
        """Test MCPError prefixes message correctly."""
        error = MCPError("Connection failed")
        assert "MCP Server Error" in error.message
        assert error.status_code == 503

    def test_tool_error_creation(self):
        """Test ToolError includes tool name."""
        error = ToolError("weather", "API timeout")
        assert "weather" in error.message
        assert error.tool_name == "weather"

    def test_validation_error_creation(self):
        """Test ValidationError includes field info."""
        error = ValidationError("Invalid format", field="email")
        assert error.field == "email"
        assert error.status_code == 400

    def test_handle_api_error_with_api_error(self):
        """Test handle_api_error returns correct response for APIError."""
        error = APIError("Test", status_code=404, details={"key": "value"})
        response, code = handle_api_error(error)
        assert code == 404
        assert response["error"] == "Test"
        assert response["details"]["key"] == "value"

    def test_handle_api_error_with_value_error(self):
        """Test handle_api_error handles ValueError correctly."""
        error = ValueError("Invalid input")
        response, code = handle_api_error(error)
        assert code == 400
        assert "Invalid value" in response["error"]

    def test_handle_api_error_with_generic_exception(self):
        """Test handle_api_error handles unknown exceptions."""
        error = RuntimeError("Something went wrong")
        response, code = handle_api_error(error)
        assert code == 500
        assert response["error"] == "Internal server error"

    def test_safe_async_call_success(self):
        """Test safe_async_call returns result on success."""
        async def success_func():
            return "success"

        result = safe_async_call(success_func)
        assert result == "success"

    def test_safe_async_call_with_default_on_error(self):
        """Test safe_async_call returns default on error."""
        async def error_func():
            raise ValueError("Test error")

        result = safe_async_call(error_func, default="default_value")
        assert result == "default_value"


class TestAsyncHelpers:
    """Tests for async helper utilities."""

    def test_run_async_decorator(self):
        """Test run_async decorator converts async to sync."""
        @run_async
        async def async_func(x: int) -> int:
            return x * 2

        # Should be callable synchronously
        result = async_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_gather_with_timeout_success(self):
        """Test gather_with_timeout runs coroutines concurrently."""
        async def coro1():
            return 1

        async def coro2():
            return 2

        results = await gather_with_timeout(coro1(), coro2(), timeout=5.0)
        assert results == [1, 2]

    @pytest.mark.asyncio
    async def test_gather_with_timeout_handles_exceptions(self):
        """Test gather_with_timeout returns exceptions when configured."""
        async def success():
            return "ok"

        async def failure():
            raise ValueError("fail")

        results = await gather_with_timeout(
            success(), failure(), timeout=5.0, return_exceptions=True
        )
        assert results[0] == "ok"
        assert isinstance(results[1], ValueError)

    @pytest.mark.asyncio
    async def test_retry_async_success_first_try(self):
        """Test retry_async returns immediately on success."""
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_async(success_func, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_async_success_after_retry(self):
        """Test retry_async retries on failure then succeeds."""
        call_count = 0

        async def eventual_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await retry_async(
            eventual_success,
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(ConnectionError,),
        )
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_exhausts_retries(self):
        """Test retry_async raises after exhausting retries."""
        async def always_fails():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            await retry_async(
                always_fails,
                max_retries=2,
                base_delay=0.01,
                retryable_exceptions=(ConnectionError,),
            )


class TestConstants:
    """Tests for constants module."""

    def test_app_version_format(self):
        """Test APP_VERSION follows semantic versioning."""
        parts = APP_VERSION.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_financial_symbols_not_empty(self):
        """Test FINANCIAL_SYMBOLS has default symbols."""
        assert len(FINANCIAL_SYMBOLS) > 0
        assert "MSFT" in FINANCIAL_SYMBOLS
        assert "BTC" in FINANCIAL_SYMBOLS

    def test_shuttle_stop_names_has_mappings(self):
        """Test SHUTTLE_STOP_NAMES has expected mappings."""
        assert "mountain_view_caltrain" in SHUTTLE_STOP_NAMES
        assert SHUTTLE_STOP_NAMES["mountain_view_caltrain"] == "Mountain View Caltrain"

    def test_todo_buckets_has_expected_values(self):
        """Test TODO_BUCKETS has standard buckets."""
        assert "work" in TODO_BUCKETS
        assert "home" in TODO_BUCKETS
        assert "personal" in TODO_BUCKETS

    def test_transport_modes_has_expected_values(self):
        """Test TRANSPORT_MODES has standard modes."""
        assert "driving" in TRANSPORT_MODES
        assert "transit" in TRANSPORT_MODES
        assert "walking" in TRANSPORT_MODES

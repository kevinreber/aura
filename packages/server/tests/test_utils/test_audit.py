"""Tests for the audit logging utility."""

import pytest
from unittest.mock import patch

from mcp_server.utils.audit import (
    audit_log, _sanitize_for_audit, _summarize_result, AuditTrail
)


class TestAuditLog:
    """Test the audit_log function."""

    def test_audit_log_basic(self):
        """Test basic audit logging."""
        with patch('mcp_server.utils.audit.audit_logger') as mock_logger:
            audit_log(
                operation="calendar.create_event",
                input_data={"title": "Test Event"},
                result={"success": True, "event_id": "123"},
                client_ip="127.0.0.1"
            )

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "AUDIT:" in call_args
            assert "calendar.create_event" in call_args

    def test_audit_log_with_user_id(self):
        """Test audit logging with user ID."""
        with patch('mcp_server.utils.audit.audit_logger') as mock_logger:
            audit_log(
                operation="todo.create",
                input_data={"title": "Test Todo"},
                result={"success": True},
                client_ip="192.168.1.1",
                user_id="user_123"
            )

            call_args = mock_logger.info.call_args[0][0]
            assert "user_123" in call_args


class TestSanitizeForAudit:
    """Test the _sanitize_for_audit function."""

    def test_sanitize_empty_data(self):
        """Test sanitizing empty data."""
        result = _sanitize_for_audit({})
        assert result == {}

    def test_sanitize_normal_data(self):
        """Test sanitizing normal data."""
        data = {"title": "Test", "description": "A test item"}
        result = _sanitize_for_audit(data)

        assert result["title"] == "Test"
        assert result["description"] == "A test item"

    def test_sanitize_sensitive_fields(self):
        """Test that sensitive fields are redacted."""
        data = {
            "title": "Test",
            "api_key": "secret_key_123",
            "password": "super_secret",
            "user_token": "token_abc"
        }
        result = _sanitize_for_audit(data)

        assert result["title"] == "Test"
        assert result["api_key"] == "[REDACTED]"
        assert result["password"] == "[REDACTED]"
        assert result["user_token"] == "[REDACTED]"

    def test_sanitize_nested_data(self):
        """Test sanitizing nested data."""
        data = {
            "event": {
                "title": "Meeting",
                "credentials": {
                    "api_key": "secret"
                }
            }
        }
        result = _sanitize_for_audit(data)

        assert result["event"]["title"] == "Meeting"
        assert result["event"]["credentials"]["api_key"] == "[REDACTED]"

    def test_sanitize_lists(self):
        """Test sanitizing lists."""
        data = {
            "attendees": ["a@example.com", "b@example.com", "c@example.com"]
        }
        result = _sanitize_for_audit(data)

        assert result["attendees"] == "[list of 3 items]"

    def test_sanitize_long_strings(self):
        """Test truncating long strings."""
        long_string = "a" * 300
        data = {"description": long_string}
        result = _sanitize_for_audit(data)

        assert len(result["description"]) < 250
        assert result["description"].endswith("...")


class TestSummarizeResult:
    """Test the _summarize_result function."""

    def test_summarize_success(self):
        """Test summarizing successful result."""
        result = {"success": True, "event_id": "abc123"}
        summary = _summarize_result(result)

        assert summary["success"] is True
        assert summary["event_id"] == "abc123"

    def test_summarize_failure(self):
        """Test summarizing failed result."""
        result = {"success": False, "message": "Event not found"}
        summary = _summarize_result(result)

        assert summary["success"] is False
        assert summary["error"] == "Event not found"

    def test_summarize_non_dict(self):
        """Test summarizing non-dict result."""
        result = "simple string"
        summary = _summarize_result(result)

        assert summary["type"] == "str"

    def test_summarize_todo_result(self):
        """Test summarizing todo result."""
        result = {
            "success": True,
            "todo": {"id": "todo_456", "title": "Test"}
        }
        summary = _summarize_result(result)

        assert summary["success"] is True
        assert summary["todo_id"] == "todo_456"


class TestAuditTrail:
    """Test the AuditTrail class."""

    def setup_method(self):
        """Clear audit trail before each test."""
        AuditTrail.clear()

    def test_add_entry(self):
        """Test adding an entry."""
        entry = {"operation": "test", "success": True}
        AuditTrail.add(entry)

        recent = AuditTrail.get_recent(1)
        assert len(recent) == 1
        assert recent[0] == entry

    def test_get_recent(self):
        """Test getting recent entries."""
        for i in range(10):
            AuditTrail.add({"operation": f"test_{i}"})

        recent = AuditTrail.get_recent(5)
        assert len(recent) == 5
        assert recent[-1]["operation"] == "test_9"

    def test_get_by_operation(self):
        """Test filtering by operation."""
        AuditTrail.add({"operation": "calendar.create"})
        AuditTrail.add({"operation": "todo.create"})
        AuditTrail.add({"operation": "calendar.create"})

        calendar_ops = AuditTrail.get_by_operation("calendar.create")
        assert len(calendar_ops) == 2

    def test_max_entries_limit(self):
        """Test that max entries limit is enforced."""
        # Add more than max entries
        for i in range(1100):
            AuditTrail.add({"operation": f"test_{i}"})

        assert len(AuditTrail._entries) <= AuditTrail._max_entries

    def test_get_stats(self):
        """Test getting audit statistics."""
        AuditTrail.add({"operation": "calendar.create", "success": True})
        AuditTrail.add({"operation": "calendar.create", "success": True})
        AuditTrail.add({"operation": "calendar.create", "success": False})
        AuditTrail.add({"operation": "todo.create", "success": True})

        stats = AuditTrail.get_stats()

        assert stats["total_entries"] == 4
        assert stats["operations"]["calendar.create"]["total"] == 3
        assert stats["operations"]["calendar.create"]["success"] == 2
        assert stats["operations"]["calendar.create"]["failed"] == 1

    def test_clear(self):
        """Test clearing the audit trail."""
        AuditTrail.add({"operation": "test"})
        AuditTrail.clear()

        assert len(AuditTrail._entries) == 0

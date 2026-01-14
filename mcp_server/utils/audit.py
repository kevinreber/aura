"""Audit logging for write operations."""

import json
from datetime import datetime
from typing import Any, Dict, Optional
from .logging import get_logger

# Dedicated audit logger
audit_logger = get_logger("audit")


def audit_log(
    operation: str,
    input_data: Dict[str, Any],
    result: Dict[str, Any],
    client_ip: Optional[str] = None,
    user_id: Optional[str] = None
) -> None:
    """
    Log an audit trail entry for write operations.

    Args:
        operation: The operation performed (e.g., "calendar.create_event")
        input_data: The input data for the operation
        result: The result of the operation
        client_ip: The client's IP address
        user_id: Optional user identifier
    """
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "operation": operation,
        "success": result.get("success", True) if isinstance(result, dict) else True,
        "client_ip": client_ip,
        "user_id": user_id,
        "input": _sanitize_for_audit(input_data),
        "result_summary": _summarize_result(result)
    }

    # Log as structured JSON for easy parsing
    audit_logger.info(f"AUDIT: {json.dumps(audit_entry)}")


def _sanitize_for_audit(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize input data for audit logging.

    Removes or masks sensitive fields.
    """
    if not data:
        return {}

    sanitized = {}
    sensitive_fields = {
        "password", "api_key", "secret", "token", "credential",
        "credit_card", "ssn", "social_security"
    }

    for key, value in data.items():
        key_lower = key.lower()

        # Check if key contains sensitive field names
        if any(sensitive in key_lower for sensitive in sensitive_fields):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_for_audit(value)
        elif isinstance(value, list):
            # For lists, just note the count
            sanitized[key] = f"[list of {len(value)} items]"
        elif isinstance(value, str) and len(value) > 200:
            # Truncate long strings
            sanitized[key] = value[:200] + "..."
        else:
            sanitized[key] = value

    return sanitized


def _summarize_result(result: Any) -> Dict[str, Any]:
    """
    Create a summary of the operation result for audit logging.
    """
    if not isinstance(result, dict):
        return {"type": type(result).__name__}

    summary = {
        "success": result.get("success", True),
    }

    # Include IDs for tracking
    if "event_id" in result:
        summary["event_id"] = result["event_id"]
    if "todo_id" in result or "id" in result.get("todo", {}):
        summary["todo_id"] = result.get("todo_id") or result.get("todo", {}).get("id")

    # Include error message if failed
    if not summary["success"] and "message" in result:
        summary["error"] = result["message"]

    return summary


class AuditTrail:
    """
    In-memory audit trail for debugging and monitoring.

    In production, this should be backed by a persistent store.
    """

    _entries: list = []
    _max_entries: int = 1000

    @classmethod
    def add(cls, entry: Dict[str, Any]) -> None:
        """Add an entry to the audit trail."""
        cls._entries.append(entry)

        # Trim if exceeding max
        if len(cls._entries) > cls._max_entries:
            cls._entries = cls._entries[-cls._max_entries:]

    @classmethod
    def get_recent(cls, count: int = 100) -> list:
        """Get recent audit entries."""
        return cls._entries[-count:]

    @classmethod
    def get_by_operation(cls, operation: str, count: int = 50) -> list:
        """Get audit entries for a specific operation."""
        matching = [
            e for e in cls._entries
            if e.get("operation") == operation
        ]
        return matching[-count:]

    @classmethod
    def clear(cls) -> None:
        """Clear the audit trail (for testing)."""
        cls._entries = []

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get audit trail statistics."""
        operations = {}
        for entry in cls._entries:
            op = entry.get("operation", "unknown")
            if op not in operations:
                operations[op] = {"total": 0, "success": 0, "failed": 0}
            operations[op]["total"] += 1
            if entry.get("success", True):
                operations[op]["success"] += 1
            else:
                operations[op]["failed"] += 1

        return {
            "total_entries": len(cls._entries),
            "operations": operations
        }

"""Unit tests for planner-service internal AI helper routes."""

import pytest
from fastapi import HTTPException

from app.api import internal_ai


def test_require_internal_ai_access_requires_token(monkeypatch) -> None:
    """Reject internal AI access when the shared token header is missing."""

    monkeypatch.setattr(internal_ai, "INTERNAL_SERVICE_TOKEN", "shared-ai-token")

    with pytest.raises(HTTPException) as exc_info:
        internal_ai.require_internal_ai_access(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Internal service token is required."


def test_require_internal_ai_access_rejects_invalid_token(monkeypatch) -> None:
    """Reject internal AI access when the shared token does not match."""

    monkeypatch.setattr(internal_ai, "INTERNAL_SERVICE_TOKEN", "shared-ai-token")

    with pytest.raises(HTTPException) as exc_info:
        internal_ai.require_internal_ai_access("wrong-token")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Internal service token is invalid."


def test_internal_ai_service_boundary_returns_planner_ownership(monkeypatch) -> None:
    """Return the planner truth boundary for trusted internal AI callers."""

    monkeypatch.setattr(internal_ai, "INTERNAL_SERVICE_TOKEN", "shared-ai-token")
    internal_ai.require_internal_ai_access("shared-ai-token")

    payload = internal_ai.get_internal_ai_service_boundary()

    assert payload["service"] == "planner-service"
    assert payload["responsibility"] == "proposals and diagnostics truth"

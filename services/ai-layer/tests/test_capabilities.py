"""Unit tests for ai-layer access control and authenticated capability routes."""

import pytest
from fastapi import HTTPException

from app.api import capabilities
from app.infrastructure.clients.core_service import AuthenticatedUserContext, CoreServiceAuthError


class StubAuthClient:
    """Stub core-service auth client used to isolate ai-layer access checks in tests."""

    def __init__(self, context: AuthenticatedUserContext | None = None, error: CoreServiceAuthError | None = None) -> None:
        """Prepare a stub introspection client with either a context or an error."""

        self.context = context
        self.error = error
        self.tokens: list[str] = []

    def introspect_access_token(self, access_token: str) -> AuthenticatedUserContext:
        """Record the incoming token and return the configured auth outcome."""

        self.tokens.append(access_token)
        if self.error is not None:
            raise self.error
        assert self.context is not None
        return self.context


def test_require_ai_layer_access_requires_authorization_header() -> None:
    """Reject capability access when the Authorization header is missing."""

    with pytest.raises(HTTPException) as exc_info:
        capabilities.require_ai_layer_access(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authorization header is required."


def test_require_ai_layer_access_denies_employee_role(monkeypatch) -> None:
    """Reject ai-layer access for employee users after token introspection."""

    monkeypatch.setattr(
        capabilities,
        "auth_client",
        StubAuthClient(
            context=AuthenticatedUserContext(
                user_id=5,
                role="employee",
                is_active=True,
                employee_id=12,
            )
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        capabilities.require_ai_layer_access("Bearer employee-token")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "You do not have access to ai-layer."


def test_require_ai_layer_access_allows_manager_role(monkeypatch) -> None:
    """Allow ai-layer access for active manager users after introspection."""

    auth_stub = StubAuthClient(
        context=AuthenticatedUserContext(
            user_id=7,
            role="manager",
            is_active=True,
            employee_id=3,
        )
    )
    monkeypatch.setattr(capabilities, "auth_client", auth_stub)

    context = capabilities.require_ai_layer_access("Bearer manager-token")

    assert context.role == "manager"
    assert auth_stub.tokens == ["manager-token"]


def test_require_ai_layer_access_returns_503_when_introspection_unavailable(monkeypatch) -> None:
    """Surface core-service introspection outages as controlled 503 responses."""

    monkeypatch.setattr(
        capabilities,
        "auth_client",
        StubAuthClient(error=CoreServiceAuthError(status_code=503, detail="core-service auth introspection is unavailable")),
    )

    with pytest.raises(HTTPException) as exc_info:
        capabilities.require_ai_layer_access("Bearer manager-token")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "core-service auth introspection is unavailable"


def test_capabilities_endpoint_returns_authenticated_runtime_metadata() -> None:
    """Return runtime capability metadata only for an authenticated manager/admin user."""

    response = capabilities.get_capabilities(
        AuthenticatedUserContext(
            user_id=11,
            role="admin",
            is_active=True,
            employee_id=None,
        )
    )

    assert response.service == "ai-layer"
    assert response.user.role == "admin"

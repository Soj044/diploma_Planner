"""HTTP clients for ai-layer authentication against core-service.

This module owns token introspection for frontend-facing ai-layer routes.
It keeps auth authority in core-service and returns a compact user context
that ai-layer can use for role checks without duplicating JWT logic locally.
"""

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class CoreServiceAuthError(Exception):
    """Raised when token introspection fails or core-service auth is unavailable."""

    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class AuthenticatedUserContext:
    """Compact user context returned by core-service token introspection."""

    user_id: int
    role: str
    is_active: bool
    employee_id: int | None


class CoreServiceAuthClient:
    """Validate ai-layer access tokens using core-service introspection."""

    def __init__(self, base_url: str, internal_service_token: str = "", timeout_seconds: float = 10.0) -> None:
        """Configure the core-service auth client with base URL and shared token."""

        self._base_url = base_url.rstrip("/")
        self._internal_service_token = internal_service_token
        self._timeout_seconds = timeout_seconds

    def introspect_access_token(self, access_token: str) -> AuthenticatedUserContext:
        """Resolve a Bearer token into a compact authenticated user context."""

        if not self._internal_service_token:
            raise CoreServiceAuthError(status_code=503, detail="ai-layer auth introspection is not configured")

        http_request = Request(
            url=f"{self._base_url}/api/v1/auth/introspect",
            data=json.dumps({"token": access_token}).encode("utf-8"),
            headers=self._build_headers(),
            method="POST",
        )

        try:
            with urlopen(http_request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = self._extract_detail(exc)
            if exc.code in {401, 403}:
                raise CoreServiceAuthError(status_code=exc.code, detail=detail) from exc
            raise CoreServiceAuthError(status_code=503, detail="core-service auth introspection is unavailable") from exc
        except URLError as exc:
            raise CoreServiceAuthError(status_code=503, detail="core-service auth introspection is unavailable") from exc

        try:
            user_id = int(payload["user_id"])
            role = str(payload["role"])
            is_active = bool(payload["is_active"])
            employee_raw = payload.get("employee_id")
            employee_id = int(employee_raw) if employee_raw is not None else None
        except (KeyError, TypeError, ValueError) as exc:
            raise CoreServiceAuthError(
                status_code=503,
                detail="core-service returned invalid introspection payload",
            ) from exc

        return AuthenticatedUserContext(
            user_id=user_id,
            role=role,
            is_active=is_active,
            employee_id=employee_id,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build headers for internal ai-layer auth introspection calls."""

        return {
            "Content-Type": "application/json",
            "X-Internal-Service-Token": self._internal_service_token,
        }

    def _extract_detail(self, error: HTTPError) -> str:
        """Extract a stable error detail from a core-service HTTP error."""

        try:
            payload = json.loads(error.read().decode("utf-8"))
        except Exception:
            return "Access token is invalid."
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail
        return "Access token is invalid."

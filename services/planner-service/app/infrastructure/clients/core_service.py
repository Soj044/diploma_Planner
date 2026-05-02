"""HTTP-клиенты planner-service для snapshot fetch и auth introspection.

Этот файл реализует boundary из application layer и забирает snapshot бизнес-
данных перед расчетом назначений. Он связывает planner orchestration с
core-service, но не владеет самими сотрудниками или задачами.
"""

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from contracts.schemas import CreatePlanRunRequest, PlanningSnapshot

from app.application.snapshot_client import SnapshotClientError


class CoreServiceAuthError(Exception):
    """Raised when token introspection fails or core auth is unavailable."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class AuthenticatedUserContext:
    """Minimal user context returned by core-service introspection."""

    user_id: int
    role: str
    is_active: bool
    employee_id: int | None


class CoreServiceSnapshotClient:
    """Fetch snapshots from core-service over HTTP."""

    def __init__(
        self,
        base_url: str,
        internal_service_token: str = "",
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._internal_service_token = internal_service_token
        self._timeout_seconds = timeout_seconds

    def fetch_snapshot(self, request: CreatePlanRunRequest) -> PlanningSnapshot:
        http_request = Request(
            url=f"{self._base_url}/api/v1/planning-snapshot/",
            data=json.dumps(request.model_dump(mode="json")).encode("utf-8"),
            headers=self._build_headers(),
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise SnapshotClientError(f"core-service returned {exc.code} while building a planning snapshot") from exc
        except URLError as exc:
            raise SnapshotClientError("core-service is unavailable for planning snapshot fetch") from exc

        try:
            return PlanningSnapshot.model_validate(payload)
        except ValidationError as exc:
            raise SnapshotClientError("core-service returned an invalid planning snapshot") from exc

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._internal_service_token:
            headers["X-Internal-Service-Token"] = self._internal_service_token
        return headers


class CoreServiceAuthClient:
    """Validate planner request access tokens using core-service introspection."""

    def __init__(self, base_url: str, internal_service_token: str = "", timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._internal_service_token = internal_service_token
        self._timeout_seconds = timeout_seconds

    def introspect_access_token(self, access_token: str) -> AuthenticatedUserContext:
        if not self._internal_service_token:
            raise CoreServiceAuthError(status_code=503, detail="planner auth introspection is not configured")

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
            raise CoreServiceAuthError(status_code=503, detail="core-service returned invalid introspection payload") from exc

        return AuthenticatedUserContext(
            user_id=user_id,
            role=role,
            is_active=is_active,
            employee_id=employee_id,
        )

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Internal-Service-Token": self._internal_service_token,
        }

    def _extract_detail(self, error: HTTPError) -> str:
        try:
            payload = json.loads(error.read().decode("utf-8"))
        except Exception:
            return "Access token is invalid."
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail
        return "Access token is invalid."

"""HTTP-клиент planner-service для получения PlanningSnapshot из core-service.

Этот файл реализует boundary из application layer и забирает snapshot бизнес-
данных перед расчетом назначений. Он связывает planner orchestration с
core-service, но не владеет самими сотрудниками или задачами.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from contracts.schemas import CreatePlanRunRequest, PlanningSnapshot

from app.application.snapshot_client import SnapshotClientError


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

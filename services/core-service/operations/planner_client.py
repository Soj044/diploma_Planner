"""HTTP client for reading persisted planner artifacts during approval handoff."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from contracts.schemas import PlanResponse


class PlannerServiceError(Exception):
    """Raised when core-service cannot read a persisted plan run from planner-service."""


class PlannerServiceClient:
    """Fetch persisted plan runs from planner-service over HTTP."""

    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def fetch_plan_run(self, plan_run_id: str) -> PlanResponse:
        """Return one persisted planner run so core can validate an approval against artifacts."""

        # Core validates manager approval against persisted planner output, not against client-supplied timing fields.
        http_request = Request(
            url=f"{self._base_url}/api/v1/plan-runs/{plan_run_id}",
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urlopen(http_request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise PlannerServiceError(f"planner-service returned {exc.code} for plan run {plan_run_id}") from exc
        except URLError as exc:
            raise PlannerServiceError("planner-service is unavailable during approval handoff") from exc

        try:
            return PlanResponse.model_validate(payload)
        except ValidationError as exc:
            raise PlannerServiceError("planner-service returned an invalid plan run payload") from exc

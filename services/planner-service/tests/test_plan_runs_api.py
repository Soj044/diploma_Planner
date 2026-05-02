from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from contracts.schemas import AssignmentProposal, CreatePlanRunRequest, PlanResponse, PlanRunArtifacts, PlanRunSummary

from app.api import plan_runs
from app.application.snapshot_client import SnapshotClientError
from app.infrastructure.clients.core_service import AuthenticatedUserContext, CoreServiceAuthError


class StubPlanRunService:
    def __init__(
        self,
        response: PlanResponse | None = None,
        error: Exception | None = None,
        get_response: PlanResponse | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.get_response = get_response
        self.payloads = []

    def create(self, payload):
        self.payloads.append(payload)
        if self.error is not None:
            raise self.error
        return self.response

    def get(self, plan_run_id: str):
        return self.get_response


class StubAuthClient:
    def __init__(self, context: AuthenticatedUserContext | None = None, error: CoreServiceAuthError | None = None) -> None:
        self.context = context
        self.error = error
        self.tokens: list[str] = []

    def introspect_access_token(self, access_token: str) -> AuthenticatedUserContext:
        self.tokens.append(access_token)
        if self.error is not None:
            raise self.error
        assert self.context is not None
        return self.context


def build_response() -> PlanResponse:
    return PlanResponse(
        summary=PlanRunSummary(
            plan_run_id="plan-1",
            status="completed",
            created_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
            planning_period_start=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc),
            planning_period_end=datetime(2026, 3, 24, 0, 0, tzinfo=timezone.utc),
            assigned_count=1,
            unassigned_count=0,
        ),
        proposals=[
            AssignmentProposal(
                task_id="task-1",
                employee_id="emp-1",
                score=5.0,
                planned_hours=3,
                start_date=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc).date(),
                end_date=datetime(2026, 3, 23, 0, 0, tzinfo=timezone.utc).date(),
            )
        ],
        unassigned=[],
        artifacts=PlanRunArtifacts(),
    )


def test_create_plan_run_accepts_create_request_payload(monkeypatch) -> None:
    stub_service = StubPlanRunService(response=build_response())
    monkeypatch.setattr(plan_runs, "service", stub_service)
    payload = CreatePlanRunRequest(
        planning_period_start="2026-03-23",
        planning_period_end="2026-03-23",
        initiated_by_user_id="manager-1",
        department_id="dep-1",
        task_ids=["task-1"],
    )

    response = plan_runs.create_plan_run(payload)

    assert response.summary.plan_run_id == "plan-1"
    assert stub_service.payloads[0].initiated_by_user_id == "manager-1"


def test_create_plan_run_returns_502_when_snapshot_fetch_fails(monkeypatch) -> None:
    stub_service = StubPlanRunService(error=SnapshotClientError("core-service returned 403 while building a planning snapshot"))
    monkeypatch.setattr(plan_runs, "service", stub_service)
    payload = CreatePlanRunRequest(
        planning_period_start="2026-03-23",
        planning_period_end="2026-03-23",
        initiated_by_user_id="manager-1",
    )

    with pytest.raises(HTTPException) as exc_info:
        plan_runs.create_plan_run(payload)

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "core-service returned 403 while building a planning snapshot"


def test_get_plan_run_returns_persisted_response(monkeypatch) -> None:
    stub_service = StubPlanRunService(get_response=build_response())
    monkeypatch.setattr(plan_runs, "service", stub_service)

    response = plan_runs.get_plan_run("plan-1")

    assert response.summary.plan_run_id == "plan-1"


def test_get_plan_run_raises_404_when_missing(monkeypatch) -> None:
    stub_service = StubPlanRunService(get_response=None)
    monkeypatch.setattr(plan_runs, "service", stub_service)

    with pytest.raises(HTTPException) as exc_info:
        plan_runs.get_plan_run("missing-plan")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Plan run not found"


def test_require_planner_access_requires_authorization_header() -> None:
    with pytest.raises(HTTPException) as exc_info:
        plan_runs.require_planner_access(None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authorization header is required."


def test_require_planner_access_denies_employee_role(monkeypatch) -> None:
    monkeypatch.setattr(
        plan_runs,
        "auth_client",
        StubAuthClient(
            context=AuthenticatedUserContext(
                user_id=10,
                role="employee",
                is_active=True,
                employee_id=77,
            )
        ),
    )
    with pytest.raises(HTTPException) as exc_info:
        plan_runs.require_planner_access("Bearer employee-token")
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "You do not have access to planner runs."


def test_require_planner_access_allows_manager_role(monkeypatch) -> None:
    auth_stub = StubAuthClient(
        context=AuthenticatedUserContext(
            user_id=1,
            role="manager",
            is_active=True,
            employee_id=3,
        )
    )
    monkeypatch.setattr(plan_runs, "auth_client", auth_stub)
    context = plan_runs.require_planner_access("Bearer manager-token")
    assert context.role == "manager"
    assert context.user_id == 1
    assert auth_stub.tokens == ["manager-token"]


def test_require_planner_access_returns_503_when_introspection_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        plan_runs,
        "auth_client",
        StubAuthClient(error=CoreServiceAuthError(status_code=503, detail="core-service auth introspection is unavailable")),
    )
    with pytest.raises(HTTPException) as exc_info:
        plan_runs.require_planner_access("Bearer manager-token")
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "core-service auth introspection is unavailable"

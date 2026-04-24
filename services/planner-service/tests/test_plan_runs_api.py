from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from contracts.schemas import AssignmentProposal, CreatePlanRunRequest, PlanResponse, PlanRunArtifacts, PlanRunSummary

from app.api import plan_runs
from app.application.snapshot_client import SnapshotClientError


class StubPlanRunService:
    def __init__(self, response: PlanResponse | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.payloads = []

    def create(self, payload):
        self.payloads.append(payload)
        if self.error is not None:
            raise self.error
        return self.response

    def get(self, plan_run_id: str):
        return None


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

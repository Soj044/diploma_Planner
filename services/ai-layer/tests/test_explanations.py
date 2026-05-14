"""Unit tests for public ai-layer explanation routes."""

from fastapi import HTTPException
import pytest

from app.api import explanations
from app.application.explanations import (
    ExplanationIndexNotReadyError,
    ExplanationResult,
    ExplanationServiceError,
    SimilarCase,
)
from app.infrastructure.clients.core_service import AuthenticatedUserContext


class StubExplanationService:
    """Stub explanation service used to isolate route-level behavior in tests."""

    def __init__(
        self,
        *,
        result: ExplanationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        """Prepare a route stub with either a success result or a service error."""

        self.result = result
        self.error = error

    def build_assignment_rationale(self, **_: object) -> ExplanationResult:
        """Return the configured assignment explanation result or raise the stub error."""

        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result

    def build_unassigned_explanation(self, **_: object) -> ExplanationResult:
        """Return the configured unassigned explanation result or raise the stub error."""

        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def _manager_context() -> AuthenticatedUserContext:
    """Build one reusable authenticated manager context for route unit tests."""

    return AuthenticatedUserContext(
        user_id=17,
        role="manager",
        is_active=True,
        employee_id=4,
    )


def _explanation_result() -> ExplanationResult:
    """Build one stable explanation payload for route success assertions."""

    return ExplanationResult(
        summary="Index returned one similar case.",
        reasons=["Reason A"],
        risks=["Risk A"],
        recommended_actions=["Action A"],
        similar_cases=[
            SimilarCase(
                headline="Indexed case",
                source_service="core-service",
                source_type="assignment_case",
                source_key="case-1",
                outcome_note="Retrieved by cosine distance 0.1000.",
            )
        ],
        advisory_note="Advisory response only.",
    )


def test_assignment_rationale_route_returns_503_when_index_is_not_ready() -> None:
    """Surface index readiness problems as controlled HTTP 503 responses."""

    with pytest.raises(HTTPException) as exc_info:
        explanations.create_assignment_rationale(
            request=explanations.AssignmentRationaleRequest(
                task_id="task-1",
                employee_id="employee-1",
                plan_run_id="run-1",
            ),
            context=_manager_context(),
            service=StubExplanationService(
                error=ExplanationIndexNotReadyError("AI retrieval index is not ready."),
            ),
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "AI retrieval index is not ready."


def test_assignment_rationale_route_returns_502_for_upstream_payload_errors() -> None:
    """Surface structured runtime payload failures as controlled HTTP 502 responses."""

    with pytest.raises(HTTPException) as exc_info:
        explanations.create_assignment_rationale(
            request=explanations.AssignmentRationaleRequest(
                task_id="task-1",
                employee_id="employee-1",
                plan_run_id="run-1",
            ),
            context=_manager_context(),
            service=StubExplanationService(
                error=ExplanationServiceError(
                    status_code=502,
                    detail="ollama returned invalid structured explanation payload",
                ),
            ),
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "ollama returned invalid structured explanation payload"


def test_assignment_rationale_route_returns_public_payload() -> None:
    """Return the stable public explanation response for assignment rationale calls."""

    response = explanations.create_assignment_rationale(
        request=explanations.AssignmentRationaleRequest(
            task_id="task-1",
            employee_id="employee-1",
            plan_run_id="run-1",
        ),
        context=_manager_context(),
        service=StubExplanationService(result=_explanation_result()),
    )

    assert response.summary == "Index returned one similar case."
    assert response.similar_cases[0].source_key == "case-1"


def test_unassigned_route_returns_public_payload() -> None:
    """Return the stable public explanation response for unassigned task calls."""

    response = explanations.create_unassigned_task_explanation(
        request=explanations.UnassignedTaskExplanationRequest(
            task_id="task-2",
            plan_run_id="run-2",
        ),
        context=_manager_context(),
        service=StubExplanationService(result=_explanation_result()),
    )

    assert response.recommended_actions == ["Action A"]

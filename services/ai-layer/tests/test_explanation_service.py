"""Unit tests for the ai-layer explanation application service."""

from dataclasses import asdict
from datetime import UTC, datetime

import pytest

from app.application.explanations import (
    ExplanationIndexNotReadyError,
    ExplanationService,
    ExplanationServiceError,
)
from app.dtos import AssignmentLiveContext, ProposalContext, UnassignedContext
from app.infrastructure.clients.core_service import AuthenticatedUserContext
from app.infrastructure.repositories.postgres import IndexSearchFilters, RetrievedIndexItem


class FakeRepository:
    """In-memory stand-in for the ai-layer PostgreSQL repository."""

    def __init__(self, retrieved_items: list[RetrievedIndexItem]) -> None:
        """Prepare the fake repository with fixed retrieval results."""

        self.retrieved_items = retrieved_items
        self.search_calls: list[dict[str, object]] = []
        self.logs: list[dict[str, object]] = []

    def search_similar_items(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: IndexSearchFilters | None = None,
    ) -> list[RetrievedIndexItem]:
        """Record one search call and return the configured retrieval records."""

        self.search_calls.append(
            {
                "query_embedding": query_embedding,
                "top_k": top_k,
                "filters": filters,
            }
        )
        return list(self.retrieved_items)

    def insert_explanation_log(self, **payload: object) -> int:
        """Record explanation log payloads and return a fake row identifier."""

        self.logs.append(payload)
        return len(self.logs)


class FakeReindexService:
    """In-memory refresh and readiness provider for explanation-service tests."""

    def __init__(
        self,
        *,
        ready: bool,
        stale_sources: set[str] | None = None,
    ) -> None:
        """Store the desired readiness and stale-refresh behavior."""

        self.ready = ready
        self.stale_sources = stale_sources or set()
        self.refresh_calls: list[list[str]] = []
        self.readiness_calls: list[dict[str, str | None]] = []

    def refresh_if_stale(self, source_services: list[str]) -> set[str]:
        """Record the requested refresh slice and return the configured stale fallback."""

        self.refresh_calls.append(list(source_services))
        return set(self.stale_sources)

    def is_index_ready(
        self,
        *,
        source_service: str | None = None,
        source_type: str | None = None,
    ) -> bool:
        """Return the configured readiness state for the requested retrieval slice."""

        self.readiness_calls.append(
            {
                "source_service": source_service,
                "source_type": source_type,
            }
        )
        return self.ready


class FakeCoreServiceClient:
    """Stub core-service client for explanation-service tests."""

    def __init__(self, assignment_context: AssignmentLiveContext) -> None:
        """Prepare one fixed live assignment context response."""

        self.assignment_context = assignment_context

    def get_assignment_context(self, *, task_id: str, employee_id: str) -> AssignmentLiveContext:
        """Return the configured live assignment context."""

        assert task_id
        assert employee_id
        return self.assignment_context


class FakePlannerServiceClient:
    """Stub planner-service client for explanation-service tests."""

    def __init__(
        self,
        *,
        proposal_context: ProposalContext,
        unassigned_context: UnassignedContext,
    ) -> None:
        """Prepare fixed persisted planner context responses."""

        self.proposal_context = proposal_context
        self.unassigned_context = unassigned_context

    def get_proposal_context(
        self,
        *,
        plan_run_id: str,
        task_id: str,
        employee_id: str,
    ) -> ProposalContext:
        """Return the configured proposal context."""

        assert plan_run_id
        assert task_id
        assert employee_id
        return self.proposal_context

    def get_unassigned_context(self, *, plan_run_id: str, task_id: str) -> UnassignedContext:
        """Return the configured unassigned-task context."""

        assert plan_run_id
        assert task_id
        return self.unassigned_context


class FakeOllamaClient:
    """Stub Ollama client used to isolate explanation-service behavior."""

    def __init__(self, *, embeddings: list[list[float]], generated_content: str) -> None:
        """Prepare the stub embedding and generation responses."""

        self.embeddings = embeddings
        self.generated_content = generated_content
        self.embedding_requests: list[list[str]] = []
        self.generate_requests: list[dict[str, object]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Record the incoming texts and return the configured embeddings."""

        self.embedding_requests.append(texts)
        return self.embeddings

    def generate_explanation(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, object] | str | None = None,
        temperature: float = 0.1,
    ) -> str:
        """Record the structured generation request and return the configured content."""

        self.generate_requests.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_schema": response_schema,
                "temperature": temperature,
            }
        )
        return self.generated_content


def _manager_context() -> AuthenticatedUserContext:
    """Build one reusable authenticated manager context for service tests."""

    return AuthenticatedUserContext(
        user_id=19,
        role="manager",
        is_active=True,
        employee_id=8,
    )


def _retrieved_item() -> RetrievedIndexItem:
    """Build one typed retrieved item for explanation-service assertions."""

    now = datetime.now(tz=UTC)
    return RetrievedIndexItem(
        id=1,
        source_service="core-service",
        source_type="assignment_case",
        source_key="assignment:1",
        title="Matched task history",
        content="Stored retrieval payload",
        metadata_json={"assignment_status": "approved", "assigned_by_type": "manager"},
        source_updated_at=now,
        created_at=now,
        updated_at=now,
        distance=0.125,
    )


def _embedding() -> list[float]:
    """Build one repository-compatible embedding vector."""

    return [0.0] * 1024


def _assignment_context() -> AssignmentLiveContext:
    """Build one typed live assignment context for service tests."""

    return AssignmentLiveContext.model_validate(
        {
            "task": {"id": "task-1", "title": "Assemble batch", "description": "Prepare shipment"},
            "requirements": [{"skill_id": "skill-1", "skill_name": "Python", "min_level": 3, "weight": 1.5}],
            "employee": {"id": "employee-1", "full_name": "Alice Worker"},
            "employee_skills": [{"skill_id": "skill-1", "skill_name": "Python", "level": 4}],
            "availability": {"schedule_days": [], "approved_leaves": [], "availability_overrides": []},
        }
    )


def _proposal_context() -> ProposalContext:
    """Build one typed proposal context for service tests."""

    return ProposalContext.model_validate(
        {
            "plan_run_summary": {"plan_run_id": "run-1", "status": "completed"},
            "task_snapshot": {"task_id": "task-1", "title": "Assemble batch"},
            "proposal": {"task_id": "task-1", "employee_id": "employee-1", "score": 95.0},
            "sibling_proposals": [{"task_id": "task-1", "employee_id": "employee-2", "score": 74.0}],
            "eligibility": {"employee_ids": ["employee-1", "employee-2"], "eligible_count": 2},
            "score_map": {"employee-1": 95.0, "employee-2": 74.0},
            "solver_summary": {"status": "OPTIMAL"},
        }
    )


def _unassigned_context() -> UnassignedContext:
    """Build one typed unassigned-task context for service tests."""

    return UnassignedContext.model_validate(
        {
            "plan_run_summary": {"plan_run_id": "run-1", "status": "completed"},
            "task_snapshot": {"task_id": "task-2", "title": "Overflow task"},
            "diagnostic": {
                "task_id": "task-2",
                "reason_code": "capacity_or_conflict",
                "message": "No capacity left",
                "reason_details": "All eligible workers are already scheduled.",
            },
            "eligibility": {"employee_ids": ["employee-1"], "eligible_count": 1},
            "score_map": {"employee-1": 65.0},
            "solver_summary": {"status": "OPTIMAL"},
        }
    )


def _generated_json() -> str:
    """Build one valid structured explanation payload returned by the fake LLM."""

    return (
        '{"summary":"Candidate looks compatible with prior assignments.",'
        '"reasons":["Strong skill match","Planner score is high"],'
        '"risks":["Availability should still be reviewed"],'
        '"recommended_actions":["Review proposal before approval"],'
        '"advisory_note":"Advisory response only."}'
    )


def test_build_assignment_rationale_raises_when_index_is_not_ready() -> None:
    """Reject explanation creation while the retrieval index is still empty."""

    service = ExplanationService(
        repository=FakeRepository(retrieved_items=[]),
        reindex_service=FakeReindexService(ready=False),
        core_service_client=FakeCoreServiceClient(_assignment_context()),
        planner_service_client=FakePlannerServiceClient(
            proposal_context=_proposal_context(),
            unassigned_context=_unassigned_context(),
        ),
        ollama_client=FakeOllamaClient(embeddings=[_embedding()], generated_content=_generated_json()),
    )

    with pytest.raises(ExplanationIndexNotReadyError) as exc_info:
        service.build_assignment_rationale(
            task_id="task-1",
            employee_id="employee-1",
            plan_run_id="run-1",
            user_context=_manager_context(),
        )

    assert str(exc_info.value) == "AI retrieval index is not ready."


def test_build_assignment_rationale_filters_retrieval_and_logs_request() -> None:
    """Log the request payload and filter vector retrieval to assignment cases only."""

    repository = FakeRepository(retrieved_items=[_retrieved_item()])
    reindex_service = FakeReindexService(ready=True)
    service = ExplanationService(
        repository=repository,
        reindex_service=reindex_service,
        core_service_client=FakeCoreServiceClient(_assignment_context()),
        planner_service_client=FakePlannerServiceClient(
            proposal_context=_proposal_context(),
            unassigned_context=_unassigned_context(),
        ),
        ollama_client=FakeOllamaClient(embeddings=[_embedding()], generated_content=_generated_json()),
    )

    result = service.build_assignment_rationale(
        task_id="task-7",
        employee_id="employee-2",
        plan_run_id="run-8",
        user_context=_manager_context(),
    )

    assert result.summary == "Candidate looks compatible with prior assignments."
    assert repository.search_calls[0]["top_k"] == 5
    filters = repository.search_calls[0]["filters"]
    assert isinstance(filters, IndexSearchFilters)
    assert filters.source_service == "core-service"
    assert filters.source_type == "assignment_case"
    assert repository.logs[0]["request_type"] == "assignment-rationale"
    assert repository.logs[0]["request_json"] == {
        "task_id": "task-7",
        "employee_id": "employee-2",
        "plan_run_id": "run-8",
    }
    assert repository.logs[0]["retrieved_keys_json"] == ["assignment:1"]
    assert repository.logs[0]["response_json"] == asdict(result)
    assert reindex_service.refresh_calls == [["core-service"]]
    assert reindex_service.readiness_calls[0] == {
        "source_service": "core-service",
        "source_type": "assignment_case",
    }


def test_build_assignment_rationale_appends_stale_note_when_refresh_fallback_is_used() -> None:
    """Mark the explanation when ai-layer had to rely on a stale retrieval slice."""

    service = ExplanationService(
        repository=FakeRepository(retrieved_items=[_retrieved_item()]),
        reindex_service=FakeReindexService(ready=True, stale_sources={"core-service"}),
        core_service_client=FakeCoreServiceClient(_assignment_context()),
        planner_service_client=FakePlannerServiceClient(
            proposal_context=_proposal_context(),
            unassigned_context=_unassigned_context(),
        ),
        ollama_client=FakeOllamaClient(embeddings=[_embedding()], generated_content=_generated_json()),
    )

    result = service.build_assignment_rationale(
        task_id="task-1",
        employee_id="employee-1",
        plan_run_id="run-1",
        user_context=_manager_context(),
    )

    assert "stale ai-layer retrieval index" in result.advisory_note
    assert "core-service" in result.advisory_note


def test_build_unassigned_explanation_raises_502_for_invalid_structured_payload() -> None:
    """Return a controlled 502 when Ollama responds with invalid structured JSON."""

    service = ExplanationService(
        repository=FakeRepository(retrieved_items=[_retrieved_item()]),
        reindex_service=FakeReindexService(ready=True),
        core_service_client=FakeCoreServiceClient(_assignment_context()),
        planner_service_client=FakePlannerServiceClient(
            proposal_context=_proposal_context(),
            unassigned_context=_unassigned_context(),
        ),
        ollama_client=FakeOllamaClient(embeddings=[_embedding()], generated_content="not-json"),
    )

    with pytest.raises(ExplanationServiceError) as exc_info:
        service.build_unassigned_explanation(
            task_id="task-2",
            plan_run_id="run-1",
            user_context=_manager_context(),
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "ollama returned invalid structured explanation payload"

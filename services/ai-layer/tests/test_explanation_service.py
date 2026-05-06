"""Unit tests for the ai-layer explanation application service."""

from dataclasses import asdict
from datetime import UTC, datetime

import pytest

from app.application.explanations import ExplanationIndexNotReadyError, ExplanationService
from app.infrastructure.clients.core_service import AuthenticatedUserContext
from app.infrastructure.repositories.postgres import RetrievedIndexItem


class FakeRepository:
    """In-memory stand-in for the ai-layer PostgreSQL repository."""

    def __init__(self, retrieved_items: list[RetrievedIndexItem]) -> None:
        """Prepare the fake repository with fixed retrieval results."""

        self.retrieved_items = retrieved_items
        self.search_calls: list[tuple[list[float], int]] = []
        self.logs: list[dict[str, object]] = []

    def search_similar_items(self, query_embedding: list[float], top_k: int) -> list[RetrievedIndexItem]:
        """Record one search call and return the configured retrieval records."""

        self.search_calls.append((query_embedding, top_k))
        return list(self.retrieved_items)

    def insert_explanation_log(self, **payload: object) -> int:
        """Record explanation log payloads and return a fake row identifier."""

        self.logs.append(payload)
        return len(self.logs)


class FakeReindexService:
    """In-memory readiness provider for explanation-service unit tests."""

    def __init__(self, *, ready: bool) -> None:
        """Store the desired readiness result for the fake service."""

        self.ready = ready

    def is_index_ready(self) -> bool:
        """Return the configured readiness state."""

        return self.ready


class FakeOllamaClient:
    """Stub embedding client used to isolate explanation-service behavior."""

    def __init__(self, embeddings: list[list[float]]) -> None:
        """Prepare the stub embedding responses."""

        self.embeddings = embeddings
        self.requests: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Record the incoming texts and return the configured embeddings."""

        self.requests.append(texts)
        return self.embeddings


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
        source_key="case-1",
        title="Matched task history",
        content="Stored retrieval payload",
        metadata_json={"kind": "assignment_case"},
        source_updated_at=now,
        created_at=now,
        updated_at=now,
        distance=0.125,
    )


def _embedding() -> list[float]:
    """Build one repository-compatible embedding vector."""

    return [0.0] * 1024


def test_build_assignment_rationale_raises_when_index_is_not_ready() -> None:
    """Reject explanation creation while the retrieval index is still empty."""

    service = ExplanationService(
        repository=FakeRepository(retrieved_items=[]),
        reindex_service=FakeReindexService(ready=False),
        core_service_client=object(),
        planner_service_client=object(),
        ollama_client=FakeOllamaClient(embeddings=[_embedding()]),
    )

    with pytest.raises(ExplanationIndexNotReadyError) as exc_info:
        service.build_assignment_rationale(
            task_id="task-1",
            employee_id="employee-1",
            plan_run_id="run-1",
            user_context=_manager_context(),
        )

    assert str(exc_info.value) == "AI retrieval index is not ready."


def test_build_assignment_rationale_logs_request_and_retrieved_keys() -> None:
    """Log the request payload and retrieved source keys after a successful explanation build."""

    repository = FakeRepository(retrieved_items=[_retrieved_item()])
    service = ExplanationService(
        repository=repository,
        reindex_service=FakeReindexService(ready=True),
        core_service_client=object(),
        planner_service_client=object(),
        ollama_client=FakeOllamaClient(embeddings=[_embedding()]),
    )

    result = service.build_assignment_rationale(
        task_id="task-7",
        employee_id="employee-2",
        plan_run_id="run-8",
        user_context=_manager_context(),
    )

    assert "task-7" in result.summary
    assert repository.search_calls[0][1] == 5
    assert repository.logs[0]["request_type"] == "assignment-rationale"
    assert repository.logs[0]["request_json"] == {
        "task_id": "task-7",
        "employee_id": "employee-2",
        "plan_run_id": "run-8",
    }
    assert repository.logs[0]["retrieved_keys_json"] == ["case-1"]
    assert repository.logs[0]["response_json"] == asdict(result)

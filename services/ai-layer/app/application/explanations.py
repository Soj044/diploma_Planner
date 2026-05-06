"""Application services for ai-layer explanations.

This module turns repository results and future runtime clients into stable
frontend-facing explanation payloads. In the current cycle the payloads remain
deterministic and advisory, but they already use the same repository and
embedding interfaces that the next retrieval-focused cycle will extend.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.application.reindex import ReindexService
from app.config import AI_TOP_K, OLLAMA_CHAT_MODEL
from app.infrastructure.clients.core_service import AuthenticatedUserContext, CoreServiceAuthClient
from app.infrastructure.clients.ollama import OllamaClient, OllamaClientError
from app.infrastructure.clients.planner_service import PlannerServiceClient
from app.infrastructure.repositories.postgres import PostgresAiRepository, RetrievedIndexItem


class ExplanationIndexNotReadyError(Exception):
    """Raised when public explanation routes are called before the index is ready."""


class ExplanationServiceUnavailableError(Exception):
    """Raised when the explanation runtime cannot build a response right now."""


@dataclass(frozen=True)
class SimilarCase:
    """One historical case summary returned to the browser."""

    headline: str
    source_service: str
    source_type: str
    source_key: str
    outcome_note: str


@dataclass(frozen=True)
class ExplanationResult:
    """Stable application-layer explanation payload exposed by ai-layer."""

    summary: str
    reasons: list[str]
    risks: list[str]
    recommended_actions: list[str]
    similar_cases: list[SimilarCase]
    advisory_note: str


class ExplanationService:
    """Build advisory explanation payloads for browser-facing ai-layer routes."""

    def __init__(
        self,
        repository: PostgresAiRepository,
        reindex_service: ReindexService,
        core_service_client: CoreServiceAuthClient,
        planner_service_client: PlannerServiceClient,
        ollama_client: OllamaClient,
        model_name: str = OLLAMA_CHAT_MODEL,
        top_k: int = AI_TOP_K,
    ) -> None:
        """Configure the explanation service with storage and runtime clients."""

        self._repository = repository
        self._reindex_service = reindex_service
        self._core_service_client = core_service_client
        self._planner_service_client = planner_service_client
        self._ollama_client = ollama_client
        self._model_name = model_name
        self._top_k = top_k

    def build_assignment_rationale(
        self,
        *,
        task_id: str,
        employee_id: str,
        plan_run_id: str,
        user_context: AuthenticatedUserContext,
    ) -> ExplanationResult:
        """Build an advisory explanation for one proposed assignment match."""

        request_payload = {
            "task_id": task_id,
            "employee_id": employee_id,
            "plan_run_id": plan_run_id,
        }
        query_text = (
            "assignment rationale "
            f"task:{task_id} employee:{employee_id} plan_run:{plan_run_id}"
        )
        return self._build_explanation(
            request_type="assignment-rationale",
            request_payload=request_payload,
            query_text=query_text,
            user_context=user_context,
        )

    def build_unassigned_explanation(
        self,
        *,
        task_id: str,
        plan_run_id: str,
        user_context: AuthenticatedUserContext,
    ) -> ExplanationResult:
        """Build an advisory explanation for one unassigned planner outcome."""

        request_payload = {
            "task_id": task_id,
            "plan_run_id": plan_run_id,
        }
        query_text = f"unassigned task explanation task:{task_id} plan_run:{plan_run_id}"
        return self._build_explanation(
            request_type="unassigned-task",
            request_payload=request_payload,
            query_text=query_text,
            user_context=user_context,
        )

    def _build_explanation(
        self,
        *,
        request_type: str,
        request_payload: dict[str, str],
        query_text: str,
        user_context: AuthenticatedUserContext,
    ) -> ExplanationResult:
        """Run the current-cycle retrieval pass and produce a stable explanation payload."""

        if not self._reindex_service.is_index_ready():
            raise ExplanationIndexNotReadyError("AI retrieval index is not ready.")

        try:
            embeddings = self._ollama_client.embed_texts([query_text])
        except OllamaClientError as exc:
            raise ExplanationServiceUnavailableError("AI explanation runtime is unavailable.") from exc

        if not embeddings:
            raise ExplanationServiceUnavailableError("AI explanation runtime is unavailable.")

        retrieved_items = self._repository.search_similar_items(
            query_embedding=embeddings[0],
            top_k=self._top_k,
        )
        result = ExplanationResult(
            summary=self._build_summary(
                request_type=request_type,
                request_payload=request_payload,
                retrieved_items=retrieved_items,
            ),
            reasons=self._build_reasons(
                request_type=request_type,
                retrieved_items=retrieved_items,
            ),
            risks=self._build_risks(),
            recommended_actions=self._build_recommended_actions(request_type=request_type),
            similar_cases=self._build_similar_cases(retrieved_items),
            advisory_note=self._build_advisory_note(),
        )
        self._repository.insert_explanation_log(
            request_type=request_type,
            user_id=user_context.user_id,
            request_json=request_payload,
            retrieved_keys_json=[item.source_key for item in retrieved_items],
            response_json=asdict(result),
            model_name=self._model_name,
        )
        return result

    def _build_summary(
        self,
        *,
        request_type: str,
        request_payload: dict[str, str],
        retrieved_items: list[RetrievedIndexItem],
    ) -> str:
        """Build a deterministic summary for the current explanation cycle."""

        related_cases = len(retrieved_items)
        if request_type == "assignment-rationale":
            return (
                "AI advisory context is available for "
                f"task {request_payload['task_id']} and employee {request_payload['employee_id']}. "
                f"The retrieval index returned {related_cases} similar historical case(s)."
            )
        return (
            "AI advisory context is available for "
            f"task {request_payload['task_id']} in plan run {request_payload['plan_run_id']}. "
            f"The retrieval index returned {related_cases} similar historical case(s)."
        )

    def _build_reasons(
        self,
        *,
        request_type: str,
        retrieved_items: list[RetrievedIndexItem],
    ) -> list[str]:
        """Build stable explanation reasons from the indexed history that was found."""

        reasons = [
            "The explanation is based on derived ai-layer retrieval data rather than new business truth.",
            f"Vector search completed successfully and returned {len(retrieved_items)} indexed historical match(es).",
        ]
        if request_type == "assignment-rationale":
            reasons.append("This response is intended to support manager review of a proposed assignment candidate.")
        else:
            reasons.append("This response is intended to support manager review of an unassigned diagnostic outcome.")
        return reasons

    def _build_risks(self) -> list[str]:
        """Describe the known limitations of the current explanation cycle."""

        return [
            "Live task and proposal context from core-service and planner-service will be wired in the next cycle.",
            "The current explanation payload is advisory and should be validated against planner and core-service screens.",
        ]

    def _build_recommended_actions(self, *, request_type: str) -> list[str]:
        """Suggest operator actions that remain within existing backend-owned flows."""

        if request_type == "assignment-rationale":
            return [
                "Review the proposed assignment in planner-service before approving it in core-service.",
                "Use the matching task and employee records in core-service as the final business-truth reference.",
            ]
        return [
            "Review the planner diagnostic details before switching to manual assignment.",
            "Confirm the task requirements and availability data in core-service before changing the assignment flow.",
        ]

    def _build_similar_cases(self, retrieved_items: list[RetrievedIndexItem]) -> list[SimilarCase]:
        """Convert retrieved index records into compact browser-facing similar case payloads."""

        return [
            SimilarCase(
                headline=item.title,
                source_service=item.source_service,
                source_type=item.source_type,
                source_key=item.source_key,
                outcome_note=f"Retrieved by cosine distance {item.distance:.4f}.",
            )
            for item in retrieved_items
        ]

    def _build_advisory_note(self) -> str:
        """Describe the ownership boundary that still governs the explanation result."""

        return (
            "Advisory response only: core-service remains the business truth, "
            "planner-service remains the proposals and diagnostics truth, and ai-layer owns only derived retrieval metadata."
        )

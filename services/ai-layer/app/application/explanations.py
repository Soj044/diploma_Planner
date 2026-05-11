"""Application services for ai-layer explanations.

This module orchestrates live context reads, retrieval-index refresh, vector
search, prompt construction, structured Ollama generation, and explanation log
storage. It keeps ai-layer advisory-only while respecting core-service and
planner-service ownership boundaries.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from app.application.reindex import ReindexService, ReindexServiceError
from app.config import AI_TOP_K, OLLAMA_CHAT_MODEL
from app.dtos import AssignmentLiveContext, ProposalContext, StructuredExplanationOutput, UnassignedContext
from app.infrastructure.clients.core_service import (
    AuthenticatedUserContext,
    CoreServiceAiReadError,
    CoreServiceAuthClient,
)
from app.infrastructure.clients.ollama import OllamaClient, OllamaClientError
from app.infrastructure.clients.planner_service import (
    PlannerServiceAiReadError,
    PlannerServiceClient,
)
from app.infrastructure.repositories.postgres import IndexSearchFilters, PostgresAiRepository, RetrievedIndexItem

STRUCTURED_EXPLANATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "recommended_actions": {"type": "array", "items": {"type": "string"}},
        "advisory_note": {"type": "string"},
    },
    "required": [
        "summary",
        "reasons",
        "risks",
        "recommended_actions",
        "advisory_note",
    ],
}
MAX_PROMPT_TEXT_CHARS = 280
MAX_PROMPT_SIMILAR_CASES = 3
MAX_PROMPT_SCORES = 5
OWNERSHIP_ADVISORY = (
    "Advisory response only: core-service remains the business truth, "
    "planner-service remains the proposals and diagnostics truth, and ai-layer "
    "owns only derived retrieval metadata and explanation rendering."
)


class ExplanationServiceError(Exception):
    """Raised when ai-layer cannot produce a stable explanation response."""

    def __init__(self, *, status_code: int, detail: str) -> None:
        """Store the HTTP-style status code and detail used by route handlers."""

        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class ExplanationIndexNotReadyError(ExplanationServiceError):
    """Raised when public explanation routes are called before the index is ready."""

    def __init__(self, detail: str = "AI retrieval index is not ready.") -> None:
        """Create the stable readiness error expected by public explanation routes."""

        super().__init__(status_code=503, detail=detail)


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
        stale_sources = self._refresh_retrieval_slice(["core-service"])
        if not self._reindex_service.is_index_ready(
            source_service="core-service",
            source_type="assignment_case",
        ):
            raise ExplanationIndexNotReadyError()

        live_context = self._read_assignment_live_context(task_id=task_id, employee_id=employee_id)
        proposal_context = self._read_proposal_context(
            plan_run_id=plan_run_id,
            task_id=task_id,
            employee_id=employee_id,
        )
        retrieved_items = self._retrieve_similar_assignment_cases(
            task_id=task_id,
            employee_id=employee_id,
            live_context=live_context,
            proposal_context=proposal_context,
        )
        structured_output = self._generate_structured_output(
            system_prompt=self._assignment_system_prompt(),
            user_prompt=self._assignment_user_prompt(
                live_context=live_context,
                proposal_context=proposal_context,
                retrieved_items=retrieved_items,
            ),
        )
        return self._finalize_result(
            request_type="assignment-rationale",
            request_payload=request_payload,
            user_context=user_context,
            structured_output=structured_output,
            retrieved_items=retrieved_items,
            stale_sources=stale_sources,
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
        stale_sources = self._refresh_retrieval_slice(["planner-service"])
        if not self._reindex_service.is_index_ready(
            source_service="planner-service",
            source_type="unassigned_case",
        ):
            raise ExplanationIndexNotReadyError()

        unassigned_context = self._read_unassigned_context(
            plan_run_id=plan_run_id,
            task_id=task_id,
        )
        retrieved_items = self._retrieve_similar_unassigned_cases(
            task_id=task_id,
            unassigned_context=unassigned_context,
        )
        structured_output = self._generate_structured_output(
            system_prompt=self._unassigned_system_prompt(),
            user_prompt=self._unassigned_user_prompt(
                unassigned_context=unassigned_context,
                retrieved_items=retrieved_items,
            ),
        )
        return self._finalize_result(
            request_type="unassigned-task",
            request_payload=request_payload,
            user_context=user_context,
            structured_output=structured_output,
            retrieved_items=retrieved_items,
            stale_sources=stale_sources,
        )

    def _refresh_retrieval_slice(self, source_services: list[str]) -> set[str]:
        """Refresh stale retrieval sources and preserve stale fallbacks when allowed."""

        try:
            return self._reindex_service.refresh_if_stale(source_services)
        except ReindexServiceError as exc:
            raise ExplanationServiceError(status_code=exc.status_code, detail=exc.detail) from exc

    def _read_assignment_live_context(self, *, task_id: str, employee_id: str) -> AssignmentLiveContext:
        """Read the live core-service assignment context used in assignment prompts."""

        try:
            return self._core_service_client.get_assignment_context(
                task_id=task_id,
                employee_id=employee_id,
            )
        except CoreServiceAiReadError as exc:
            raise ExplanationServiceError(status_code=exc.status_code, detail=exc.detail) from exc

    def _read_proposal_context(
        self,
        *,
        plan_run_id: str,
        task_id: str,
        employee_id: str,
    ) -> ProposalContext:
        """Read the persisted planner proposal context used in assignment prompts."""

        try:
            return self._planner_service_client.get_proposal_context(
                plan_run_id=plan_run_id,
                task_id=task_id,
                employee_id=employee_id,
            )
        except PlannerServiceAiReadError as exc:
            raise ExplanationServiceError(status_code=exc.status_code, detail=exc.detail) from exc

    def _read_unassigned_context(
        self,
        *,
        plan_run_id: str,
        task_id: str,
    ) -> UnassignedContext:
        """Read the persisted planner unassigned context used in diagnostic prompts."""

        try:
            return self._planner_service_client.get_unassigned_context(
                plan_run_id=plan_run_id,
                task_id=task_id,
            )
        except PlannerServiceAiReadError as exc:
            raise ExplanationServiceError(status_code=exc.status_code, detail=exc.detail) from exc

    def _retrieve_similar_assignment_cases(
        self,
        *,
        task_id: str,
        employee_id: str,
        live_context: AssignmentLiveContext,
        proposal_context: ProposalContext,
    ) -> list[RetrievedIndexItem]:
        """Retrieve similar indexed assignment cases for one proposal explanation."""

        query_text = self._dump_json(
            {
                "task_id": task_id,
                "employee_id": employee_id,
                "task_summary": self._task_summary(live_context.task),
                "requirements": self._requirements_summary(live_context.requirements),
                "employee_summary": self._employee_summary(live_context.employee),
                "employee_skills": self._employee_skills_summary(live_context.employee_skills),
                "availability_summary": self._availability_summary(live_context.availability),
                "selected_proposal": self._proposal_summary(proposal_context.proposal),
                "eligibility_summary": self._eligibility_summary(proposal_context.eligibility),
                "score_summary": self._score_summary(proposal_context.score_map),
            }
        )
        return self._search_similar_items(
            query_text=query_text,
            filters=IndexSearchFilters(
                source_service="core-service",
                source_type="assignment_case",
            ),
        )

    def _retrieve_similar_unassigned_cases(
        self,
        *,
        task_id: str,
        unassigned_context: UnassignedContext,
    ) -> list[RetrievedIndexItem]:
        """Retrieve similar indexed unassigned cases for one diagnostic explanation."""

        query_text = self._dump_json(
            {
                "task_id": task_id,
                "task_summary": self._task_summary(unassigned_context.task_snapshot),
                "diagnostic": self._diagnostic_summary(unassigned_context.diagnostic),
                "eligibility_summary": self._eligibility_summary(unassigned_context.eligibility),
                "score_summary": self._score_summary(unassigned_context.score_map),
                "solver_summary": self._solver_summary(unassigned_context.solver_summary),
            }
        )
        return self._search_similar_items(
            query_text=query_text,
            filters=IndexSearchFilters(
                source_service="planner-service",
                source_type="unassigned_case",
            ),
        )

    def _search_similar_items(
        self,
        *,
        query_text: str,
        filters: IndexSearchFilters,
    ) -> list[RetrievedIndexItem]:
        """Embed one retrieval query and search the filtered pgvector corpus."""

        try:
            embeddings = self._ollama_client.embed_texts([query_text])
        except OllamaClientError as exc:
            raise ExplanationServiceError(status_code=exc.status_code, detail=exc.detail) from exc
        if not embeddings:
            raise ExplanationServiceError(status_code=502, detail="ollama embedding payload is invalid")
        return self._repository.search_similar_items(
            query_embedding=embeddings[0],
            top_k=self._top_k,
            filters=filters,
        )

    def _generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> StructuredExplanationOutput:
        """Run the local Ollama chat call and validate its strict JSON response."""

        try:
            raw_content = self._ollama_client.generate_explanation(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=STRUCTURED_EXPLANATION_SCHEMA,
                temperature=0.1,
            )
        except OllamaClientError as exc:
            raise ExplanationServiceError(status_code=exc.status_code, detail=exc.detail) from exc

        try:
            raw_payload = json.loads(raw_content)
        except ValueError as exc:
            raise ExplanationServiceError(
                status_code=502,
                detail="ollama returned invalid structured explanation payload",
            ) from exc

        try:
            return StructuredExplanationOutput.model_validate(raw_payload)
        except Exception as exc:  # pydantic validation should become a stable 502.
            raise ExplanationServiceError(
                status_code=502,
                detail="ollama returned invalid structured explanation payload",
            ) from exc

    def _assignment_system_prompt(self) -> str:
        """Build the stable system prompt for assignment rationale explanations."""

        return (
            "You explain planner assignment proposals for managers. "
            "Use only the provided live context, persisted planner context, and historical similar cases. "
            "Do not invent missing facts, do not override planner decisions, and keep the answer advisory. "
            "Return strict JSON that matches the provided schema."
        )

    def _unassigned_system_prompt(self) -> str:
        """Build the stable system prompt for unassigned-task explanations."""

        return (
            "You explain why a planner run left a task unassigned. "
            "Use only the provided persisted planner context and historical similar cases. "
            "Do not invent missing facts, do not replace solver logic, and keep the answer advisory. "
            "Return strict JSON that matches the provided schema."
        )

    def _assignment_user_prompt(
        self,
        *,
        live_context: AssignmentLiveContext,
        proposal_context: ProposalContext,
        retrieved_items: list[RetrievedIndexItem],
    ) -> str:
        """Build the assignment-rationale user prompt with live and historical context."""

        return "\n\n".join(
            [
                f"ownership_boundary={OWNERSHIP_ADVISORY}",
                f"task_summary={self._dump_json(self._task_summary(live_context.task))}",
                f"requirements={self._dump_json(self._requirements_summary(live_context.requirements))}",
                f"employee_summary={self._dump_json(self._employee_summary(live_context.employee))}",
                f"employee_skills={self._dump_json(self._employee_skills_summary(live_context.employee_skills))}",
                f"availability_summary={self._dump_json(self._availability_summary(live_context.availability))}",
                f"selected_proposal={self._dump_json(self._proposal_summary(proposal_context.proposal))}",
                f"sibling_proposals={self._dump_json(self._sibling_proposals_summary(proposal_context.sibling_proposals))}",
                f"eligibility_summary={self._dump_json(self._eligibility_summary(proposal_context.eligibility))}",
                f"score_summary={self._dump_json(self._score_summary(proposal_context.score_map))}",
                f"solver_summary={self._dump_json(self._solver_summary(proposal_context.solver_summary))}",
                f"similar_cases={self._dump_json(self._retrieved_cases_prompt_payload(retrieved_items))}",
            ]
        )

    def _unassigned_user_prompt(
        self,
        *,
        unassigned_context: UnassignedContext,
        retrieved_items: list[RetrievedIndexItem],
    ) -> str:
        """Build the unassigned-task user prompt with persisted and historical context."""

        return "\n\n".join(
            [
                f"ownership_boundary={OWNERSHIP_ADVISORY}",
                f"task_summary={self._dump_json(self._task_summary(unassigned_context.task_snapshot))}",
                f"diagnostic={self._dump_json(self._diagnostic_summary(unassigned_context.diagnostic))}",
                f"eligibility_summary={self._dump_json(self._eligibility_summary(unassigned_context.eligibility))}",
                f"score_summary={self._dump_json(self._score_summary(unassigned_context.score_map))}",
                f"solver_summary={self._dump_json(self._solver_summary(unassigned_context.solver_summary))}",
                f"similar_cases={self._dump_json(self._retrieved_cases_prompt_payload(retrieved_items))}",
            ]
        )

    def _task_summary(self, task_payload: dict[str, Any]) -> dict[str, Any]:
        """Project one task payload into a compact prompt-friendly summary."""

        task_summary = self._pick_fields(
            task_payload,
            (
                "id",
                "task_id",
                "title",
                "priority",
                "status",
                "department_id",
                "estimated_hours",
                "start_date",
                "due_date",
                "starts_at",
                "ends_at",
            ),
        )
        description = task_payload.get("description")
        if isinstance(description, str) and description.strip():
            task_summary["description"] = self._compact_text(description)
        return task_summary

    def _requirements_summary(self, requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Reduce task requirements to the fields useful for explanation prompts."""

        return [
            self._pick_fields(requirement, ("skill_id", "skill_name", "min_level", "weight"))
            for requirement in requirements
        ]

    def _employee_summary(self, employee_payload: dict[str, Any]) -> dict[str, Any]:
        """Project one employee payload into a compact prompt-friendly summary."""

        return self._pick_fields(
            employee_payload,
            ("id", "employee_id", "full_name", "department_id", "position_name", "is_active"),
        )

    def _employee_skills_summary(self, employee_skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Reduce employee skill payloads to the fields needed by explanations."""

        return [
            self._pick_fields(skill_payload, ("skill_id", "skill_name", "level"))
            for skill_payload in employee_skills
        ]

    def _availability_summary(self, availability_payload: dict[str, Any]) -> dict[str, Any]:
        """Summarize live availability without sending every schedule row verbatim."""

        schedule_days = availability_payload.get("schedule_days")
        approved_leaves = availability_payload.get("approved_leaves")
        availability_overrides = availability_payload.get("availability_overrides")
        return {
            "schedule_day_count": len(schedule_days) if isinstance(schedule_days, list) else 0,
            "approved_leave_count": len(approved_leaves) if isinstance(approved_leaves, list) else 0,
            "availability_override_count": len(availability_overrides)
            if isinstance(availability_overrides, list)
            else 0,
            "approved_leave_dates": self._date_window_summary(approved_leaves),
            "override_dates": self._date_window_summary(availability_overrides),
        }

    def _proposal_summary(self, proposal_payload: dict[str, Any]) -> dict[str, Any]:
        """Reduce one selected proposal payload to compact planner facts."""

        return self._pick_fields(
            proposal_payload,
            (
                "task_id",
                "employee_id",
                "score",
                "rank",
                "planned_hours",
                "status",
                "start_date",
                "end_date",
                "is_selected",
            ),
        )

    def _sibling_proposals_summary(self, proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep only a short summary of competing proposals for the same task."""

        return [
            self._pick_fields(proposal, ("employee_id", "score", "rank", "status", "is_selected"))
            for proposal in proposals[:MAX_PROMPT_SIMILAR_CASES]
        ]

    def _eligibility_summary(self, eligibility_payload: dict[str, Any]) -> dict[str, Any]:
        """Reduce eligibility payloads to counts and a short employee sample."""

        summary = self._pick_fields(eligibility_payload, ("eligible_count",))
        employee_ids = eligibility_payload.get("employee_ids")
        if isinstance(employee_ids, list):
            summary["employee_ids"] = [str(employee_id) for employee_id in employee_ids[:MAX_PROMPT_SCORES]]
        return summary

    def _score_summary(self, score_map: dict[str, float]) -> list[dict[str, Any]]:
        """Return the top planner scores in descending order for prompt compactness."""

        score_items = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
        return [
            {"employee_id": employee_id, "score": round(float(score), 4)}
            for employee_id, score in score_items[:MAX_PROMPT_SCORES]
        ]

    def _solver_summary(self, solver_payload: dict[str, Any]) -> dict[str, Any]:
        """Reduce solver payloads to stable top-level facts only."""

        return self._pick_fields(
            solver_payload,
            ("status", "objective_value", "wall_time_seconds", "assigned_count", "unassigned_count"),
        )

    def _diagnostic_summary(self, diagnostic_payload: dict[str, Any]) -> dict[str, Any]:
        """Reduce one unassigned diagnostic payload to the key explanation facts."""

        summary = self._pick_fields(diagnostic_payload, ("task_id", "reason_code"))
        message = diagnostic_payload.get("message")
        if isinstance(message, str) and message.strip():
            summary["message"] = self._compact_text(message)
        reason_details = diagnostic_payload.get("reason_details")
        if isinstance(reason_details, str) and reason_details.strip():
            summary["reason_details"] = self._compact_text(reason_details)
        return summary

    def _retrieved_cases_prompt_payload(self, retrieved_items: list[RetrievedIndexItem]) -> list[dict[str, Any]]:
        """Serialize retrieved rows into short prompt-friendly historical case summaries."""

        prompt_cases: list[dict[str, Any]] = []
        for item in retrieved_items[:MAX_PROMPT_SIMILAR_CASES]:
            prompt_cases.append(
                {
                    "headline": item.title,
                    "source_key": item.source_key,
                    "distance": round(item.distance, 4),
                    "summary_note": self._similar_case_outcome(item),
                    "content_excerpt": self._compact_text(item.content, limit=180),
                }
            )
        return prompt_cases

    def _date_window_summary(self, rows: Any) -> list[dict[str, Any]]:
        """Project date-like ranges into a short list for prompt summaries."""

        if not isinstance(rows, list):
            return []
        return [
            self._pick_fields(
                row if isinstance(row, dict) else {},
                ("date", "start_date", "end_date", "starts_at", "ends_at", "status"),
            )
            for row in rows[:MAX_PROMPT_SIMILAR_CASES]
        ]

    def _pick_fields(self, payload: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
        """Copy only non-empty fields that matter for AI prompt compactness."""

        result: dict[str, Any] = {}
        for field_name in fields:
            value = payload.get(field_name)
            if value in (None, "", [], {}):
                continue
            result[field_name] = value
        return result

    def _finalize_result(
        self,
        *,
        request_type: str,
        request_payload: dict[str, str],
        user_context: AuthenticatedUserContext,
        structured_output: StructuredExplanationOutput,
        retrieved_items: list[RetrievedIndexItem],
        stale_sources: set[str],
    ) -> ExplanationResult:
        """Build the final public explanation payload and persist one explanation log."""

        advisory_note = structured_output.advisory_note.strip() or OWNERSHIP_ADVISORY
        if stale_sources:
            stale_list = ", ".join(sorted(stale_sources))
            advisory_note = (
                f"{advisory_note} Note: this explanation used a stale ai-layer retrieval index for {stale_list}."
            )

        result = ExplanationResult(
            summary=structured_output.summary,
            reasons=list(structured_output.reasons),
            risks=list(structured_output.risks),
            recommended_actions=list(structured_output.recommended_actions),
            similar_cases=self._build_similar_cases(retrieved_items),
            advisory_note=advisory_note,
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

    def _build_similar_cases(self, retrieved_items: list[RetrievedIndexItem]) -> list[SimilarCase]:
        """Convert retrieved index records into compact browser-facing similar case payloads."""

        return [
            SimilarCase(
                headline=item.title,
                source_service=item.source_service,
                source_type=item.source_type,
                source_key=item.source_key,
                outcome_note=self._similar_case_outcome(item),
            )
            for item in retrieved_items
        ]

    def _similar_case_outcome(self, item: RetrievedIndexItem) -> str:
        """Build one compact note that explains why a retrieved case is relevant."""

        if item.source_type == "assignment_case":
            assignment_status = item.metadata_json.get("assignment_status")
            assigned_by_type = item.metadata_json.get("assigned_by_type")
            return (
                f"Historical assignment status {assignment_status or 'unknown'} "
                f"via {assigned_by_type or 'unknown'}; cosine distance {item.distance:.4f}."
            )
        reason_code = item.metadata_json.get("reason_code")
        return f"Historical unassigned reason {reason_code or 'unknown'}; cosine distance {item.distance:.4f}."

    def _dump_json(self, payload: object) -> str:
        """Serialize one prompt payload into stable compact JSON text."""

        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    def _compact_text(self, value: str, *, limit: int = MAX_PROMPT_TEXT_CHARS) -> str:
        """Normalize whitespace and cap large text blocks before prompt serialization."""

        normalized = " ".join(value.split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 3].rstrip()}..."

"""Общие pydantic-контракты между core-service и planner-service.

Этот файл задает DTO для запуска планирования, передачи snapshot-данных,
возврата proposals и approval handoff. На него одновременно опираются
planner-service при расчете назначений и core-service при валидации итоговых
утверждений.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


PlanRunStatus = Literal["created", "running", "completed", "failed"]
ProposalStatus = Literal["proposed", "approved", "rejected", "applied"]
CandidateOutcomeCode = Literal[
    "selected",
    "eligible_not_selected_lower_score",
    "eligible_not_selected_capacity_or_conflict",
    "rejected_inactive_employee",
    "rejected_department_mismatch",
    "rejected_missing_required_skill",
    "rejected_insufficient_available_hours",
]


class SkillRequirement(BaseModel):
    skill_id: str
    min_level: int = Field(default=1, ge=1)
    weight: float = Field(default=1.0, ge=0)


class EmployeeAvailability(BaseModel):
    start_at: datetime
    end_at: datetime
    available_hours: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_period(self) -> "EmployeeAvailability":
        if self.start_at >= self.end_at:
            raise ValueError("availability start_at must be before end_at")
        return self


class EmployeeSnapshot(BaseModel):
    employee_id: str
    department_id: str | None = None
    is_active: bool = True
    skill_levels: dict[str, int] = Field(default_factory=dict)
    availability: list[EmployeeAvailability] = Field(default_factory=list)


class TaskSnapshot(BaseModel):
    task_id: str
    department_id: str | None = None
    title: str
    starts_at: datetime
    ends_at: datetime
    estimated_hours: int | None = Field(default=None, ge=1)
    requirements: list[SkillRequirement] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_period(self) -> "TaskSnapshot":
        if self.starts_at >= self.ends_at:
            raise ValueError("task starts_at must be before ends_at")
        return self


class PlanningSnapshot(BaseModel):
    planning_period_start: datetime
    planning_period_end: datetime
    employees: list[EmployeeSnapshot]
    tasks: list[TaskSnapshot]

    @model_validator(mode="after")
    def validate_period_and_tasks(self) -> "PlanningSnapshot":
        if self.planning_period_start >= self.planning_period_end:
            raise ValueError("planning_period_start must be before planning_period_end")
        for task in self.tasks:
            if task.starts_at < self.planning_period_start or task.ends_at > self.planning_period_end:
                raise ValueError("all tasks must be inside the planning period")
        return self


class PlanRequest(PlanningSnapshot):
    """Bootstrap request shape that embeds a full planning snapshot."""


class CreatePlanRunRequest(BaseModel):
    planning_period_start: date
    planning_period_end: date
    initiated_by_user_id: str
    department_id: str | None = None
    task_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_period(self) -> "CreatePlanRunRequest":
        if self.planning_period_start > self.planning_period_end:
            raise ValueError("planning_period_start must be before or equal to planning_period_end")
        return self


class AssignmentProposal(BaseModel):
    task_id: str
    employee_id: str
    score: float
    proposal_rank: int = 1
    is_selected: bool = True
    planned_hours: int | None = Field(default=None, ge=1)
    start_date: date | None = None
    end_date: date | None = None
    status: ProposalStatus = "proposed"
    explanation_text: str = ""

    @model_validator(mode="after")
    def validate_dates(self) -> "AssignmentProposal":
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("assignment proposal must include both start_date and end_date")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("assignment proposal start_date must be before or equal to end_date")
        return self


class UnassignedTaskDiagnostic(BaseModel):
    task_id: str
    reason_code: Literal["no_eligible_candidates", "capacity_or_conflict"]
    message: str
    reason_details: str = ""


class PlanRunSummary(BaseModel):
    plan_run_id: str
    status: PlanRunStatus = "completed"
    created_at: datetime
    planning_period_start: datetime | None = None
    planning_period_end: datetime | None = None
    assigned_count: int
    unassigned_count: int


class CandidateAnalysisRow(BaseModel):
    """Persisted planner-side explanation facts for one task/employee comparison."""

    employee_id: str
    outcome_code: CandidateOutcomeCode
    eligible: bool
    score: float | None = None
    selected: bool = False
    available_hours_in_window: float | None = Field(default=None, ge=0)
    required_hours: int | None = Field(default=None, ge=1)
    missing_skill_ids: list[str] = Field(default_factory=list)
    missing_skill_names: list[str] = Field(default_factory=list)
    matched_department: bool = True


class PlanRunArtifacts(BaseModel):
    eligibility: dict[str, list[str]] = Field(default_factory=dict)
    scores: dict[str, dict[str, float]] = Field(default_factory=dict)
    solver_statistics: dict[str, int | float | str] = Field(default_factory=dict)
    candidate_analysis: dict[str, list[CandidateAnalysisRow]] = Field(default_factory=dict)


class PlanResponse(BaseModel):
    summary: PlanRunSummary
    proposals: list[AssignmentProposal]
    unassigned: list[UnassignedTaskDiagnostic]
    artifacts: PlanRunArtifacts

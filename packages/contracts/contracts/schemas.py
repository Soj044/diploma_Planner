"""Shared Pydantic schemas for planning contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SkillRequirement(BaseModel):
    skill_id: str
    min_level: int = Field(default=1, ge=1)


class EmployeeAvailability(BaseModel):
    start_at: datetime
    end_at: datetime


class EmployeeSnapshot(BaseModel):
    employee_id: str
    department_id: str
    is_active: bool = True
    skill_levels: dict[str, int] = Field(default_factory=dict)
    availability: list[EmployeeAvailability] = Field(default_factory=list)


class TaskSnapshot(BaseModel):
    task_id: str
    department_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    requirements: list[SkillRequirement] = Field(default_factory=list)


class PlanRequest(BaseModel):
    planning_period_start: datetime
    planning_period_end: datetime
    employees: list[EmployeeSnapshot]
    tasks: list[TaskSnapshot]


class AssignmentProposal(BaseModel):
    task_id: str
    employee_id: str
    score: float


class UnassignedTaskDiagnostic(BaseModel):
    task_id: str
    reason_code: Literal["no_eligible_candidates", "capacity_or_conflict"]
    message: str


class PlanRunSummary(BaseModel):
    plan_run_id: str
    created_at: datetime
    assigned_count: int
    unassigned_count: int


class PlanRunArtifacts(BaseModel):
    eligibility: dict[str, list[str]] = Field(default_factory=dict)
    scores: dict[str, dict[str, float]] = Field(default_factory=dict)
    solver_statistics: dict[str, int | float | str] = Field(default_factory=dict)


class PlanResponse(BaseModel):
    summary: PlanRunSummary
    proposals: list[AssignmentProposal]
    unassigned: list[UnassignedTaskDiagnostic]
    artifacts: PlanRunArtifacts

"""Internal result types shared across the planner pipeline.

This module keeps compact dataclasses for hard-filter traces, eligibility, and
scoring so planning stages can exchange typed facts without binding themselves
to API or persistence layers.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CandidateEligibilityTrace:
    """One hard-filter trace that explains how a candidate behaved for one task."""

    employee_id: str
    is_active: bool
    matched_department: bool
    eligible: bool
    available_hours_in_window: float
    required_hours: int
    missing_skill_ids: list[str] = field(default_factory=list)
    missing_skill_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EligibilityResult:
    """Eligible employee ids plus per-candidate hard-filter traces for each task."""

    by_task: dict[str, list[str]]
    traces_by_task: dict[str, list[CandidateEligibilityTrace]] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreResult:
    """Deterministic score map for candidates that survived eligibility."""

    by_task: dict[str, dict[str, float]]

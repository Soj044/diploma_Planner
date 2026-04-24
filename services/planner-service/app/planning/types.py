"""Internal planning result types."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EligibilityResult:
    by_task: dict[str, list[str]]


@dataclass(frozen=True)
class ScoreResult:
    by_task: dict[str, dict[str, float]]

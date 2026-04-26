"""Внутренние типы результатов planning pipeline.

Этот файл хранит простые dataclass-структуры для eligibility и scoring, чтобы
planning модули обменивались понятными типами без прямой привязки к API слою
или persistence.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EligibilityResult:
    by_task: dict[str, list[str]]


@dataclass(frozen=True)
class ScoreResult:
    by_task: dict[str, dict[str, float]]

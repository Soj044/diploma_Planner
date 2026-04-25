"""Контракт хранения planner artifacts для задач и назначений.

Этот файл описывает абстракцию репозитория plan runs, snapshots, proposals и
diagnostics. Его используют application use cases, чтобы planner мог менять
способ хранения без изменения planning business logic.
"""

from typing import Protocol

from contracts.schemas import CreatePlanRunRequest, PlanResponse, PlanningSnapshot


class PlanRunRepository(Protocol):
    def save(
        self,
        command: CreatePlanRunRequest,
        snapshot: PlanningSnapshot,
        response: PlanResponse,
    ) -> None:
        """Persist a finished plan run and its MVP artifacts."""

    def get(self, plan_run_id: str) -> PlanResponse | None:
        """Return a saved plan run response by public run id."""

# contracts

Общие pydantic-схемы для интеграции `core-service` и `planner-service`.

## MVP contracts

- `CreatePlanRunRequest` — будущий публичный command для запуска планирования по периоду и scope.
- `PlanningSnapshot` / `PlanRequest` — bootstrap-срез входных данных для planner-service.
- `AssignmentProposal`, `UnassignedTaskDiagnostic`, `PlanResponse` — результат расчета для review/approval flow.

## Validation rules

- `CreatePlanRunRequest` не допускает период, где `planning_period_end < planning_period_start`.
- `PlanningSnapshot` не допускает задачи вне planning window.
- `AssignmentProposal` требует согласованные даты назначения: либо обе даты отсутствуют, либо обе заполнены и `start_date <= end_date`.

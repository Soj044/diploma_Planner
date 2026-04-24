# contracts

Общие pydantic-схемы для интеграции `core-service` и `planner-service`.

## MVP contracts

- `CreatePlanRunRequest` — будущий публичный command для запуска планирования по периоду и scope.
- `PlanningSnapshot` / `PlanRequest` — bootstrap-срез входных данных для planner-service.
- `AssignmentProposal`, `UnassignedTaskDiagnostic`, `PlanResponse` — результат расчета для review/approval flow.

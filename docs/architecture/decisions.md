# Architecture Decisions

## ADR-001: MVP Monorepo Bootstrap

- Date: 2026-03-21
- Status: accepted

### Context
Проект стартует с нуля для дипломной MVP-версии. Требуется минимальная, чистая структура без AI-усложнений.

### Decision
- Использовать монорепо с тремя верхнеуровневыми зонами:
  - `services/core-service`
  - `services/planner-service`
  - `packages/contracts`
- Реализовывать последовательно:
  1. `core-service`
  2. `planner-service`
  3. AI-слой только после стабилизации MVP.
- Использовать OR-Tools CP-SAT как основной оптимизационный механизм planner-service.

### Consequences
- Плюсы: проще контроль контрактов, меньше дублирования, предсказуемый MVP scope.
- Минусы: на старте ниже скорость параллельной разработки, чем при full multi-agent split.

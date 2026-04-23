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

## ADR-002: Runtime and Dependency Management for MVP

- Date: 2026-03-21
- Status: accepted

### Context
Проект должен запускаться без локальной ручной установки сервисов на хост-машину.

### Decision
- Использовать Poetry как менеджер зависимостей в каждом backend-сервисе.
- Использовать Docker Compose для локального MVP runtime.
- Использовать PostgreSQL как основную БД для `core-service`.
- Хранить planner артефакты в памяти на первом MVP шаге (без отдельной БД planner).

### Consequences
- Плюсы: предсказуемый запуск, повторяемое окружение, готовность к CI.
- Минусы: planner persistence нужно будет расширить в следующих итерациях.

## ADR-003: Core-Service MVP Schema Alignment

- Date: 2026-04-23
- Status: accepted

### Context
`docs/dbdiagrams/core_service.md` defines the target MVP business schema. The bootstrap implementation used one simplified `operations` app and Django's built-in user model.

### Decision
- Add a dedicated `users` app with a custom Django user model before the schema grows.
- Keep business entities in the `operations` app for now to avoid premature app fragmentation.
- Align model fields, choices, timestamps, constraints, and indexes with the core DB diagram.
- Replace the bootstrap migration with clean initial migrations because there is no production data.

### Consequences
- Плюсы: schema ближе к дипломной модели, кастомный пользователь зафиксирован рано, CRUD остается простым.
- Минусы: initial migration reset допустим только пока проект находится в bootstrap-стадии.

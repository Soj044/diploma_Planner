# Core-Service MVP Backlog

## Goal
Keep `core-service` as the source of truth for users, employees, schedules, tasks, and final assignments.

## Ground Rules
- `users` owns the custom Django user model and roles.
- `operations` owns MVP business models until the schema stabilizes.
- `core-service` stores final approved assignments; planner proposals are not business truth.
- Keep DRF endpoints thin and admin-friendly for the diploma MVP.

## Phase 1: Schema Alignment
- Align Django models with `docs/dbdiagrams/core_service.md`.
- Use code-level `TextChoices` for enums.
- Keep one clean initial migration set while the project has no production data.

## Phase 2: CRUD And Admin
- Expose basic CRUD endpoints for users and all core business entities.
- Register all MVP entities in Django admin.
- Avoid complex permissions and workflow automation until MVP planning works.

## Phase 3: Validation And Tests
- Test required fields, unique pairs, date ranges, schedule weekday values, and default statuses.
- Keep validations focused on data needed by planner snapshots.
- Add API smoke tests for the core CRUD surface.

## Phase 4: Planner Snapshot Boundary
- Export stable planning snapshots from core data.
- Ensure planner receives copied business truth and uses only logical external IDs.
- Keep approved assignment creation in `core-service`.

## Phase 5: Approval Handoff
- Accept selected planner proposal data through an authenticated core endpoint.
- Create approved `Assignment` records and assignment change logs in `core-service`.
- Keep planner proposal status as artifact metadata, not final business truth.

## Explicitly Out of Scope For This Stage
- Frontend flows.
- Advanced permissions.
- Notifications.
- RAG/LLM or AI scoring.

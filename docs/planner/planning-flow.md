# Planning Flow

1. Manager creates tasks in core-service
2. Planner receives planning request
3. Planner creates plan run
4. Planner builds input snapshot
5. Planner performs eligibility filtering
6. Planner calculates candidate scores
7. Planner runs optimization
8. Planner returns assignment proposals
9. Manager reviews persisted proposals from `planner-service`
10. Manager submits `task + employee + source_plan_run_id` to `core-service`
11. `core-service` re-reads the persisted planner run, validates the selected proposal, and stores the approved assignment

## MVP implementation notes

- The public planner-service boundary is `CreatePlanRunRequest`.
- Planner run endpoints require `Authorization: Bearer <access_token>` and are allowed only for `admin` and `manager`.
- Planner-service validates access tokens through `core-service /api/v1/auth/introspect`.
- Planner-service fetches `PlanningSnapshot` from `core-service` truth before running eligibility, scoring, and optimization.
- Snapshot now includes bounded `historical_tasks` (completed tasks with non-null `actual_hours`) for planner-side effort estimation.
- Planner builds one `task_effort_map` (`manual|history|blended|rules`) before eligibility and reuses the same `effective_hours` across eligibility, optimization, proposals, and diagnostics.
- For non-manual estimates only, planner caps `effective_hours` by the inclusive weekday task window using a generic `8h` per weekday upper bound so task dates meaningfully constrain auto-estimation.
- A full `PlanningSnapshot` payload remains acceptable only for internal planning tests and low-level pipeline checks.
- The stable service boundary is `CreatePlanRunRequest` plus a snapshot built from `core-service` truth.
- Planner stores run artifacts and diagnostics, but final assignments remain in `core-service`.
- Planner persistence starts with run, snapshot, proposals, unassigned diagnostics, and solver statistics only.
- Planner persisted artifacts now also include `time_estimates` metadata per task, so manager review can see estimate source and effective hours.
- MVP approval handoff uses `GET /api/v1/plan-runs/{id}` for review and `POST /api/v1/assignments/approve-proposal/` in `core-service` for final approval.
- `core-service` never trusts assignment timing from the client approval payload; it copies `planned_hours`, `start_date`, and `end_date` from the persisted planner proposal.

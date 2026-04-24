# Planning Flow

1. Manager creates tasks in core-service
2. Planner receives planning request
3. Planner creates plan run
4. Planner builds input snapshot
5. Planner performs eligibility filtering
6. Planner calculates candidate scores
7. Planner runs optimization
8. Planner returns assignment proposals
9. Manager approves proposals
10. Approved proposals are submitted to `core-service`
11. Approved assignments are stored in core-service

## MVP implementation notes

- The first planner implementation may receive a full `PlanningSnapshot` payload for local testing.
- The stable service boundary is `CreatePlanRunRequest` plus a snapshot built from `core-service` truth.
- Planner stores run artifacts and diagnostics, but final assignments remain in `core-service`.
- Planner persistence starts with run, snapshot, proposals, unassigned diagnostics, and solver statistics only.
- MVP approval handoff uses `POST /api/v1/assignments/approve-proposal/` in `core-service`.

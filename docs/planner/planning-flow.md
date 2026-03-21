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
10. Approved assignments are stored in core-service
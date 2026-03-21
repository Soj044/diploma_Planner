# Project Brief

## Goal
Automated operational planning and task assignment system.

## Main idea
The system stores employees, skills, schedules, leaves, tasks, and approved assignments.
It generates assignment proposals for a planning period and allows manager approval.

## Services
- core-service (Django + DRF)
- planner-service (FastAPI + OR-Tools / CP-SAT)
- ai-layer (future RAG/LLM support)
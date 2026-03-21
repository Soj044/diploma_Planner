# Agent Workflow

## 1. Intake
- Read the task carefully.
- Identify business goal, scope boundaries, and acceptance criteria.
- Record assumptions explicitly when requirements are incomplete.
- In solo-maintainer mode, do not block on external approval; instead, keep assumptions and reasoning visible in task output.

## 2. Analysis & Architecture
- Check whether the task affects:
  - domain model
  - service boundaries
  - API contracts
  - planning flow
  - database schema
- If architecture is affected, update:
  - `docs/architecture/overview.md`
  - `docs/architecture/decisions.md`
  - `docs/architecture/diagrams.md`
- Consider non-functional concerns when relevant:
  - correctness
  - maintainability
  - performance
  - reliability

## 3. Planning
- Split work into small safe steps.
- Prefer this order:
  1. inspect existing code
  2. propose minimal change plan
  3. implement
  4. verify
  5. update docs
- Do not mix unrelated refactoring into a focused task.

## 4. Execution
- Implement only the scope needed for the current task.
- Keep changes minimal and reversible.
- Prefer explicit, testable code.
- Keep framework layers thin where possible.
- Put business logic in services/use-case modules instead of views/routes when appropriate.

## 5. Verification
- Run the most relevant checks available for the task.
- Examples:
  - tests
  - lint
  - type checks
  - migrations check
  - local startup commands
- If something cannot be verified, state it explicitly.

## 6. Documentation
- Update impacted docs in the same task.
- Update diagrams when architecture, data flow, or critical workflows change.
- Update testing guidance if behavior changed.
- Keep docs aligned with implementation.

## 7. Handoff
Always report:
- scope completed
- files changed
- verification commands run
- residual risks / follow-ups
- docs updated
- diagram update status
- assumptions made

## 8. Done Criteria
A task is complete when:
- acceptance criteria are addressed
- implementation matches project architecture
- impacted docs are updated
- verification evidence is provided
- architecture changes are documented when relevant
- no silent assumptions remain hidden
- the result is usable by the next development step
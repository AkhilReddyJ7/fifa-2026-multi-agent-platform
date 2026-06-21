---
name: Feature / Agent Task
about: Scoped implementation task for an agent or human contributor
title: "[Phase X] Short description"
labels: agent-task
assignees: ""
---

## Phase Reference

<!-- Which roadmap phase does this task belong to? -->
**Phase:** <!-- e.g. Phase 4B — Redis Checkpointing -->
**Roadmap entry:** <!-- Quote the one-line goal from docs/ROADMAP.md -->
**Stable tag at time of issue creation:** <!-- e.g. phase-4c-auth-stable -->

---

## Goal

<!-- One paragraph. What problem does this solve, and why now? -->

---

## Acceptance Criteria

<!-- Specific, testable conditions. Each criterion must be verifiable by the QA Agent. -->
<!-- Use checkboxes. Do not mark them here — they are checked during the QA review. -->

- [ ] <!-- Criterion 1 -->
- [ ] <!-- Criterion 2 -->
- [ ] <!-- Criterion 3 -->

---

## Affected Files

<!-- List files the Implementation Agent must read before writing any code. -->
<!-- Derived from the roadmap "Files affected" notes and the architecture doc. -->

```
backend/
  app/
```

---

## Files That Must NOT Change

<!-- Any files outside scope. Be explicit. -->

- `backend/tests/conftest.py` — unless the task explicitly requires a new fixture
- `infra/` — unless the task requires infrastructure changes
- Any file not listed under "Affected Files" above

---

## Test Requirements

<!-- What tests must exist when this task is done? -->

| Behavior | Test location | Existing or new? |
|---|---|---|
| <!-- describe behavior --> | `tests/...` | New |

**Test count baseline:** <!-- Copy from docs/PROJECT_STATE.md at time of issue creation -->
**Minimum test count after merge:** <!-- Baseline + expected new tests -->

---

## Implementation Notes

<!-- Any design constraints the agent must respect. Reference docs/DECISIONS.md where relevant. -->

---

## Definition of Done

- [ ] `ruff check app tests` exits 0
- [ ] `pytest tests/ -q` exits 0, count ≥ minimum above
- [ ] No file exceeds 500 lines
- [ ] `docs/PROJECT_STATE.md` updated if this closes a phase
- [ ] `docs/DECISIONS.md` updated if new technical debt is introduced
- [ ] PR description filled using `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] No commits made without Akhil's approval

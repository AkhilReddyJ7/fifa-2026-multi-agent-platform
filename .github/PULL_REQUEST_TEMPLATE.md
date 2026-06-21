# Pull Request

## Issue

Closes #<!-- issue number -->

**Phase:** <!-- e.g. Phase 4B — Redis Checkpointing -->
**Branch:** <!-- e.g. phase-4b-redis-checkpointing -->
**Base branch:** `main`

---

## Summary

<!-- Two to four sentences: what changed, why, and what it enables. -->

---

## Files Changed

<!-- Every file touched, with a one-line description of the change. -->

| File | Change |
|---|---|
| `backend/app/...` | <!-- what changed --> |

---

## Mandatory Check Results

Run from `backend/`. All three must be recorded. Do not leave these blank.

```
ruff check app tests
# Result: PASS / FAIL
# Output (if FAIL):

mypy app --ignore-missing-imports --no-strict-optional
# Result: PASS / WARNINGS (list them) / FAIL
# Output:

pytest tests/ -q
# Result: X passed, Y warnings in Z.XXs
# Previous count (from docs/PROJECT_STATE.md):
# Delta:
```

---

## Test Coverage

| New behavior | Test case | File |
|---|---|---|
| <!-- behavior --> | `test_...` | `tests/...` |

**Tests added:** <!-- count -->
**Tests removed or modified:** <!-- count and reason, or "none" -->

---

## Acceptance Criteria

<!-- Copy from the issue. Check each one. Do not leave unchecked items — resolve them first. -->

- [ ] <!-- Criterion 1 -->
- [ ] <!-- Criterion 2 -->
- [ ] <!-- Criterion 3 -->

---

## Architecture / Debt Impact

<!-- Did this change introduce new technical debt? -->
<!-- If yes, confirm it was added to docs/DECISIONS.md under "Known Technical Debt Summary". -->

- [ ] No new technical debt introduced
- [ ] New debt documented in `docs/DECISIONS.md` (TD-## added)

<!-- If this changes an architectural decision, note it here. -->

---

## Documentation Updates

- [ ] `docs/PROJECT_STATE.md` updated (if phase completed or status changed)
- [ ] `docs/ROADMAP.md` updated (if phase moved from Remaining to Completed)
- [ ] `docs/DECISIONS.md` updated (if new decision or debt recorded)
- [ ] `docs/ARCHITECTURE.md` updated (if topology, schema, or stack changed)

---

## Rollback

**Stable tag to roll back to if this merge causes a regression:** `<!-- e.g. phase-4c-auth-stable -->`

Rollback command:
```bash
git checkout phase-4c-auth-stable
```

---

## Reviewer Notes

<!-- For the Reviewer Agent: findings, caveats, or anything Akhil should know before merging. -->

---

## Human Approval Gate

> This PR must not be merged until Akhil has reviewed and explicitly approved it.
> Agents do not merge. Agents do not push. Akhil decides.

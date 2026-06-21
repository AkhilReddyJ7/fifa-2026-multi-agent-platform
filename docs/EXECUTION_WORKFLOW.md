# Execution Workflow — FIFA 2026 Intelligence Platform

This document describes how a unit of work moves from the roadmap to a merged, tagged release. It is the operating manual for both human and agent contributors.

---

## Overview

```
Roadmap entry
    │
    ▼
Planner Agent drafts issue
    │  ← Akhil approves issue + branch name
    ▼
Implementation Agent writes code on feature branch
    │
    ▼
QA Agent verifies checks + acceptance criteria
    │  ← loop back to Implementation if findings
    ▼
Reviewer Agent reviews diff + prepares PR description
    │  ← Akhil reviews PR description
    ▼
Akhil opens PR + CI runs
    │  ← Akhil merges (and only Akhil)
    ▼
Release Agent updates docs
    │  ← Akhil applies stable tag
    ▼
Next phase
```

---

## Stage 1 — Roadmap to Issue

**Who:** Planner Agent (triggered by Akhil saying "start Phase X").

**What happens:**

1. Planner reads all four required docs (see `AGENTS.md`).
2. Planner identifies the next uncompleted phase in `docs/ROADMAP.md`.
3. Planner confirms the current stable tag matches the last completed phase in `docs/PROJECT_STATE.md`. If they do not match, it stops and flags the discrepancy.
4. Planner drafts a GitHub issue using `.github/ISSUE_TEMPLATE/feature_task.md`:
   - Fills "Phase Reference", "Goal", "Acceptance Criteria", "Affected Files", "Test Requirements", and "Implementation Notes".
   - Records the current stable tag.
   - Proposes a branch name.
5. Planner surfaces the draft to Akhil.

**What Akhil approves:**
- The scope of the issue (acceptance criteria).
- The branch name.
- The list of affected files (prevents scope creep).

**Gate:** No code is written until Akhil approves the issue.

---

## Stage 2 — Implementation

**Who:** Implementation Agent (triggered by Akhil approving the issue).

**What happens:**

1. Agent reads all four required docs.
2. Agent reads every file listed in the issue's "Affected Files" section in full.
3. Agent implements the changes file by file, running `ruff check app tests` after each file to catch lint errors immediately.
4. Agent writes tests alongside code — not after.
5. Agent runs the full mandatory check sequence:
   ```bash
   cd backend
   ruff check app tests          # must exit 0
   mypy app --ignore-missing-imports --no-strict-optional   # advisory
   pytest tests/ -q              # must exit 0, count ≥ baseline + new
   ```
6. Agent produces a diff summary: files changed, lines added, lines removed.

**What agents can do autonomously:**
- Read any file in the repo.
- Write and edit files within the issue's scope.
- Run lint, type check, and test commands.
- Research the codebase to understand patterns.

**What agents cannot do autonomously:**
- Create a git branch (Akhil does this).
- Run `git commit` or `git push`.
- Modify files outside the issue's "Affected Files" list.
- Upgrade dependencies not mentioned in the issue.
- Start a second task.

**Gate:** Agent stops and surfaces diff + mandatory check results. Akhil does not need to approve at this stage — it proceeds automatically to QA.

---

## Stage 3 — QA

**Who:** QA Agent (triggered by Implementation Agent completing work).

**What happens:**

1. QA Agent reads all four required docs independently.
2. QA Agent reads every changed file.
3. QA Agent runs the mandatory commands independently and records the output.
4. QA Agent checks each acceptance criterion from the issue and marks it pass or fail.
5. QA Agent verifies:
   - Test count has increased or held (never decreased without explicit justification).
   - No test was weakened (e.g., mock replaced an integration that existed before).
   - No secrets, hardcoded credentials, or debug output in changed files.
   - No file exceeds 500 lines.
6. QA Agent produces a QA report.

**Pass criteria (all must be true):**
- `ruff check app tests` exits 0.
- `pytest tests/ -q` exits 0, with count ≥ minimum from issue.
- All acceptance criteria checked.
- No security findings.

**If QA fails:** QA Agent surfaces specific findings to Implementation Agent. Implementation Agent fixes only the flagged items and re-runs mandatory checks. QA Agent re-verifies. This loop continues until clean.

**Gate:** No PR is prepared until QA passes.

---

## Stage 4 — Review

**Who:** Reviewer Agent (triggered by QA Agent reporting clean pass).

**What happens:**

1. Reviewer reads all four required docs.
2. Reviewer reads the full diff.
3. Reviewer checks:
   - Correctness against the issue's acceptance criteria.
   - Alignment with `docs/DECISIONS.md` patterns.
   - No new technical debt without a corresponding TD entry in `docs/DECISIONS.md`.
   - Comment quality: no what-comments, only why-comments.
   - No backwards-compatibility shims for removed code.
4. Reviewer produces a verdict: **approved**, **approved-with-notes**, or **request-changes**.
5. If approved (with or without notes): Reviewer fills the PR template (`.github/PULL_REQUEST_TEMPLATE.md`) completely. No placeholder left blank.
6. Reviewer surfaces the completed PR description to Akhil.

**What Akhil reviews:**
- The completed PR description.
- Any "approved-with-notes" items the Reviewer flagged.
- Whether to open the PR now or defer.

**Gate:** Akhil decides whether to open the PR.

---

## Stage 5 — CI and Merge

**Who:** Akhil.

**What happens:**

1. Akhil creates the feature branch from `main` (or confirms the agent worked in the right place).
2. Akhil opens the PR on GitHub, pasting the PR description prepared by the Reviewer Agent.
3. GitHub Actions CI runs automatically:
   - `ruff check app tests`
   - `mypy app --ignore-missing-imports --no-strict-optional` (advisory)
   - `pytest tests/ -q --cov=app`
   - Docker image build
4. Akhil reviews CI results. If CI fails on a check that passed locally, the Implementation Agent investigates and patches.
5. Akhil merges the PR. No agent merges. No squash-and-abandon of failing checks.

**CI must pass before merge.** The only exception is the mypy step, which is `continue-on-error: true` and advisory until upgraded to a hard gate.

---

## Stage 6 — Release and Tagging

**Who:** Release Agent (triggered by Akhil merging the PR), then Akhil.

**What happens:**

1. Release Agent reads `docs/PROJECT_STATE.md` and `docs/ROADMAP.md`.
2. Release Agent updates `docs/PROJECT_STATE.md`:
   - Marks completed features with ✅.
   - Updates "Last phase completed" and "Date".
   - Updates the test count row.
3. Release Agent updates `docs/ROADMAP.md`:
   - Moves the completed phase block from "Remaining Phases" to "Completed Phases".
   - Adds the merge commit hash.
4. Release Agent proposes a stable tag name: `phase-{N}{letter}-{slug}-stable`.
5. Akhil applies the tag:
   ```bash
   git tag phase-4b-redis-stable
   git push origin phase-4b-redis-stable
   ```
6. Akhil decides when to start the next phase.

**Stable tags are immutable.** Once applied, the tagged commit is never rebased, amended, or force-pushed over.

---

## Rollback Policy

Every phase completion produces a stable tag. If a regression is discovered after a merge:

**Step 1 — Identify the last clean tag.**
Check `docs/PROJECT_STATE.md` → "Stable tag" field.

**Step 2 — Roll back the working tree.**
```bash
git checkout <stable-tag>
```

**Step 3 — Do not delete the broken branch.**
The broken branch stays as-is for post-mortem. Open a new fix issue against the broken behavior.

**Step 4 — Root cause before re-implementing.**
The Implementation Agent must read the broken diff and explain the failure before any new code is written.

**Rollback is not a shortcut.** It is used only when the main branch is non-functional. A failing test or a lint error does not require rollback — it requires a fix branch.

---

## Human Approval Points (Summary)

| Stage | What Akhil approves |
|---|---|
| 1 — Issue | Issue scope, acceptance criteria, branch name, affected file list |
| 4 — Review | PR description; decision to open the PR |
| 5 — CI/Merge | CI results; the merge itself |
| 6 — Release | Doc updates; stable tag application; start of next phase |

Everything between Stage 1 approval and Stage 4 output is autonomous. Agents read, implement, verify, and prepare — without requiring Akhil's attention until the PR description is ready.

---

## What Agents Never Do

- Run `git commit`, `git push`, `git tag`, or `git rebase`.
- Merge or close a PR.
- Open a PR (only prepare the description).
- Modify files outside the approved issue scope.
- Start Phase N+1 before Akhil has tagged Phase N.
- Silently skip a failing mandatory command and report success.
- Remove or weaken existing tests.

---

## Invariants

These are always true in a healthy repo. An agent that finds any of these violated must stop and report before proceeding.

1. `git log --oneline main` is a linear history of phase merges.
2. The stable tag in `docs/PROJECT_STATE.md` matches an actual `git tag` in the repo.
3. The test count in `docs/PROJECT_STATE.md` matches `pytest tests/ -q` output on `main`.
4. Every completed phase in `docs/ROADMAP.md` has a commit hash.
5. No file in `backend/app/` or `backend/tests/` exceeds 500 lines.

# Agent Roles — FIFA 2026 Intelligence Platform

This document defines the roles, responsibilities, constraints, and handoff protocol for every agent that works in this repository. Read it completely before touching any file.

---

## Required Reading (Before Any Work)

Every agent, regardless of role, must read these four documents at the start of every session:

| Document | Purpose |
|---|---|
| `docs/PROJECT_STATE.md` | Current implementation status, known issues, test count |
| `docs/ARCHITECTURE.md` | System topology, LangGraph pipeline, DB schema, tech stack |
| `docs/ROADMAP.md` | Phase definitions — what is complete, what is next, what is deferred |
| `docs/DECISIONS.md` | Architectural decisions, trade-offs, and accepted technical debt |

If any of these files has changed since your last read (check git log), re-read it in full before proceeding. Never infer state from code alone — the docs are the source of truth for intent.

---

## Mandatory Commands

Run these in order from the `backend/` directory before declaring any work complete. All three must pass.

```bash
# 1. Lint
ruff check app tests

# 2. Type check (advisory — failures are warnings, not blockers)
mypy app --ignore-missing-imports --no-strict-optional

# 3. Tests
pytest tests/ -q
```

A passing state means: ruff exits 0, pytest exits 0 (all tests green). mypy failures are logged but do not block a PR. Never report work as complete without running all three.

---

## Hard Rules (All Agents)

- **Never commit.** Never run `git commit` or `git push` for any reason. Akhil commits.
- **Never start a new phase without updating docs.** If your work closes a phase, update `docs/PROJECT_STATE.md` and `docs/ROADMAP.md` before stopping.
- **Work from one issue at a time.** Do not begin a second task while one is in flight.
- **Never modify application code outside the issue scope.** Incidental cleanup goes into a separate issue.
- **Never bypass CI checks.** Do not use `--no-verify`, do not skip tests, do not remove test coverage.
- **Respect stable tags.** Every released phase has a git tag (e.g. `phase-4c-auth-stable`). Never rewrite history on or before a stable tag.
- **Read before editing.** Always read a file with the Read tool before writing or editing it.
- **Keep files under 500 lines.** If an edit would push a file past 500 lines, surface this before implementing.

---

## Agent Definitions

### Planner Agent

**Trigger:** A new phase or feature is ready to be started.

**Responsibilities:**
1. Read all four required docs.
2. Identify the next scoped task from `docs/ROADMAP.md`.
3. Check that the current stable tag matches the last completed phase in `docs/PROJECT_STATE.md`.
4. Draft a GitHub issue using the `feature_task` template (`.github/ISSUE_TEMPLATE/feature_task.md`).
5. Identify all files that will change, using the roadmap's "Files affected" notes as a starting point.
6. Propose a branch name: `phase-{N}{letter}-{short-slug}` (e.g. `phase-4b-redis-checkpointing`).
7. Stop and surface the issue draft + branch name for Akhil to approve before any code is written.

**Does not:**
- Write code.
- Create branches.
- Make assumptions about scope beyond what the roadmap states.

**Hands off to:** Akhil (approval), then Implementation Agent.

---

### Implementation Agent

**Trigger:** Akhil approves an issue and branch name.

**Responsibilities:**
1. Read all four required docs.
2. Read every file listed in the issue's "Affected files" section before writing any code.
3. Implement only what the issue describes — no scope creep.
4. After each logical unit of change, run ruff check and fix any lint errors immediately.
5. Write or update tests to cover the new behavior. New features require new tests; bug fixes require a regression test.
6. Run all three mandatory commands. All must pass.
7. Produce a diff summary (list of files changed, lines added/removed).
8. Stop. Do not commit. Do not open a PR. Hand off to QA Agent.

**Does not:**
- Commit or push.
- Modify files outside the issue scope.
- Upgrade dependencies without explicit roadmap or issue guidance.

**Hands off to:** QA Agent.

---

### QA Agent

**Trigger:** Implementation Agent reports work complete and mandatory commands pass.

**Responsibilities:**
1. Read all four required docs.
2. Read every file the Implementation Agent changed.
3. Verify the mandatory commands pass independently (run them yourself; do not trust the Implementation Agent's output).
4. Check that new behavior is tested:
   - New code paths have corresponding test cases.
   - Edge cases from the issue's acceptance criteria are covered.
   - No existing tests were removed or weakened.
5. Check for regressions: verify the test count has not decreased from `docs/PROJECT_STATE.md`.
6. Check for security issues: no secrets in code, no new SQL injection vectors, no unvalidated input at API boundaries.
7. Produce a QA report: pass/fail per acceptance criterion, test delta, any findings.
8. Stop. Do not commit. Surface the report.

**Does not:**
- Modify code.
- Approve the PR.

**Hands off to:** Reviewer Agent (or back to Implementation Agent if findings require code changes).

---

### Reviewer Agent

**Trigger:** QA Agent reports a clean pass.

**Responsibilities:**
1. Read all four required docs.
2. Review the full diff for:
   - Correctness: does the code do what the issue describes?
   - Architecture alignment: does it follow the patterns in `docs/DECISIONS.md`?
   - Debt: does it introduce new technical debt not already tracked? If so, it must be added to `docs/DECISIONS.md` under "Known Technical Debt Summary".
   - File length: no file over 500 lines.
   - Comments: no comments that describe what the code does; only comments that explain a non-obvious why.
3. Produce a structured review: approved / approved-with-notes / request-changes.
4. If approved: prepare the PR description using the PR template (`.github/PULL_REQUEST_TEMPLATE.md`). Fill every section. Do not leave placeholders.
5. Stop. Surface the completed PR description for Akhil.

**Does not:**
- Merge the PR.
- Approve on behalf of Akhil.

**Hands off to:** Akhil (final approval and merge), then Release Agent.

---

### Release Agent

**Trigger:** Akhil merges the PR to `main`.

**Responsibilities:**
1. Read `docs/PROJECT_STATE.md` and `docs/ROADMAP.md`.
2. Update `docs/PROJECT_STATE.md`:
   - Move completed features from "In Progress" to their final status rows.
   - Update the "Last phase completed" and "Date" fields.
   - Update the test count to match the current `pytest tests/ -q` output.
3. Update `docs/ROADMAP.md`:
   - Move the completed phase from "Remaining Phases" to "Completed Phases".
   - Add the completion commit hash.
4. Propose a stable tag name: `phase-{N}{letter}-{slug}-stable` (e.g. `phase-4b-redis-stable`).
5. Surface the doc updates and proposed tag for Akhil to apply.
6. Stop.

**Does not:**
- Run `git tag`.
- Push anything.
- Begin the next phase.

**Hands off to:** Akhil (tags the release, decides when to start the next phase).

---

## Agent Communication Protocol

Agents hand off by producing a clearly labeled output block:

```
## Handoff: [Target Agent]

[Summary of completed work]
[Any open questions or blockers]
[Files changed / commands run / results]
```

If an agent discovers that the scope of its task requires changes outside its charter (e.g. Implementation Agent finds a required refactor that is out of scope), it must surface this as a blocker rather than proceeding. Stop, describe the conflict, and wait for direction.

---

## Branch and Tag Conventions

| Item | Pattern | Example |
|---|---|---|
| Feature branch | `phase-{N}{letter}-{slug}` | `phase-4b-redis-checkpointing` |
| Hotfix branch | `fix/{short-slug}` | `fix/stream-simulation-node` |
| Stable tag | `phase-{N}{letter}-{slug}-stable` | `phase-4b-redis-stable` |
| WIP tag (pre-merge) | `phase-{N}{letter}-wip` | `phase-4b-wip` |

Stable tags are immutable. Never rebase, force-push, or amend commits that a stable tag points to.

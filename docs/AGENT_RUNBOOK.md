# Agent Runbook — FIFA 2026 Intelligence Platform

How to generate an implementation prompt from a task file and hand it to an agent.

---

## What the Runner Does

`scripts/agent_task_runner.py` reads a task file (`tasks/*.md`) and all five project docs,
then writes a single self-contained prompt. The prompt includes:

- The agent's role and all hard rules from `AGENTS.md`
- Full content of `PROJECT_STATE.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `DECISIONS.md`
- The complete task definition (goal, scope, file lists, acceptance criteria, test specs)
- The exact mandatory check commands, copy-paste ready
- Explicit stop conditions (no commit, no push, no scope creep)
- The expected output format the agent must produce

The agent receives one document and needs nothing else to start. No prior conversation
context is required.

---

## Prerequisites

- Python 3.12, no additional packages (uses stdlib only)
- Run from the **repo root** (the directory that contains `AGENTS.md`)
- The task file must exist under `tasks/`

---

## Running the Runner

### One-liner (stdout → clipboard on macOS)

```bash
python scripts/agent_task_runner.py tasks/phase_4b_redis_checkpointing.md | pbcopy
```

### Save to a file

```bash
python scripts/agent_task_runner.py tasks/phase_4b_redis_checkpointing.md \
  --output /tmp/phase_4b_prompt.md
```

### Make target (from repo root)

```bash
make agent-task TASK=tasks/phase_4b_redis_checkpointing.md
```

The default `TASK` value if omitted is `tasks/phase_4b_redis_checkpointing.md`:

```bash
make agent-task   # uses the default task
```

To pipe to clipboard with Make:

```bash
make agent-task TASK=tasks/phase_4b_redis_checkpointing.md | pbcopy
```

---

## Using the Prompt with an Agent

### Claude Code (CLI)

Paste the prompt as the first message in a new Claude Code session.
The session starts cold — no context from prior conversations is needed or wanted.

```
$ claude
> [paste the generated prompt]
```

The agent will read the embedded docs, read the affected source files, implement,
run mandatory checks, and produce a structured report. You do not need to intervene
until the agent outputs the "Handoff" line.

### Claude.ai (web)

Open a new conversation. Paste the prompt. The embedded docs give the model everything
it needs. If the prompt exceeds the paste limit, save it to a file and upload it.

### Any LLM with a system prompt

Use the full generated prompt as the system prompt. Leave the user turn empty or write:
`Begin. Read the project context, then implement the task.`

---

## What the Agent Produces

When complete, the agent outputs a structured report with these sections:

1. **Diff Summary** — every file changed with line counts
2. **Mandatory Check Results** — literal terminal output from ruff, mypy, pytest
3. **Test Delta** — every new test function with a one-line description
4. **Acceptance Criteria Status** — PASS/FAIL per criterion
5. **Handoff** — "Implementation complete. Ready for QA Agent." or a blocker statement

You review this output to decide whether to proceed to QA.

---

## What Still Requires Human Approval

The runner and the agent are fully autonomous between issue approval and the PR description.
Four decisions remain yours:

| Decision | When |
|---|---|
| Approve the issue scope and branch name | Before `make agent-task` is run |
| Approve the PR description | After Reviewer Agent prepares it |
| Merge the PR | After CI passes |
| Apply the stable tag and start the next phase | After the merge |

Everything else — reading, implementing, checking, and reporting — is autonomous.

---

## Creating a New Task File

Copy the structure of `tasks/phase_4b_redis_checkpointing.md`. Required sections:

| Section | Purpose |
|---|---|
| Header block | Phase, roadmap goal, stable tag, branch, test baseline and minimum |
| Goal | One paragraph — what problem is solved, why now |
| Scope | In scope / out of scope bullet lists |
| Files Allowed to Change | Exact paths from `backend/` |
| Files Not Allowed to Change | Explicit exclusion list |
| Acceptance Criteria | Numbered, independently verifiable, QA-checkable |
| Mandatory Tests | Function names (prescriptive), what each covers |
| Implementation Notes | Design decisions, API patterns, known trade-offs |
| Rollback Notes | Stable tag + `git checkout` command |

Acceptance criteria must be checkable by the QA Agent without human interpretation.
"The feature works" is not a criterion. "Endpoint returns 200 with `session_id` field when
called with a valid JWT" is a criterion.

---

## Running the Mandatory Checks Yourself

The `make check` target runs the same three commands the agent must run:

```bash
make check
```

This is equivalent to:

```bash
cd backend
ruff check app tests
mypy app --ignore-missing-imports --no-strict-optional
pytest tests/ -q
```

Run this before handing a task to an agent to confirm the baseline is green.
If it is not green, resolve it first — agents should never start from a broken baseline.

---

## Troubleshooting

**`ERROR: Required file not found`**
The runner looks for docs relative to the repo root (`AGENTS.md`, `docs/`, etc.).
Run from the repo root, not from inside `backend/` or `scripts/`.

**`ERROR: Required file not found: tasks/...`**
The task file path is relative to the CWD or the repo root. Check the path exists:
```bash
ls tasks/
```

**Agent modifies files outside the allowed list**
This is a hard rule violation. The agent must stop. Re-run with a fresh session and
explicitly add the file list to your first message: "Only modify the files listed in the
'Files Allowed to Change' section. Stop immediately if you need to touch anything else."

**Agent tries to commit**
Terminate the session immediately. Check `git status` to confirm nothing was staged.
The prompt's stop conditions are explicit — if an agent ignores them, do not retry with
the same session. Start fresh and consider adding an even more prominent stop condition
to the task file.

**Test count went down**
This is a blocker. The agent must not proceed. Re-run the agent with the QA report
flagging the specific tests that were removed and require them to be restored.

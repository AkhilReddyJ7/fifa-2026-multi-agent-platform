"""agent_task_runner.py — Build a self-contained implementation prompt from a task file.

Usage:
    python scripts/agent_task_runner.py <task-file>
    python scripts/agent_task_runner.py <task-file> --output <prompt-file>

Examples:
    python scripts/agent_task_runner.py tasks/phase_4b_redis_checkpointing.md
    python scripts/agent_task_runner.py tasks/phase_4b_redis_checkpointing.md --output /tmp/prompt.md
    python scripts/agent_task_runner.py tasks/phase_4b_redis_checkpointing.md | pbcopy

The generated prompt is a complete, self-contained brief for an Implementation Agent.
It embeds all required project docs so the agent can start cold with no prior context.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent

REQUIRED_DOCS: list[tuple[str, Path]] = [
    ("AGENTS.md", REPO_ROOT / "AGENTS.md"),
    ("docs/PROJECT_STATE.md", REPO_ROOT / "docs" / "PROJECT_STATE.md"),
    ("docs/ARCHITECTURE.md", REPO_ROOT / "docs" / "ARCHITECTURE.md"),
    ("docs/ROADMAP.md", REPO_ROOT / "docs" / "ROADMAP.md"),
    ("docs/DECISIONS.md", REPO_ROOT / "docs" / "DECISIONS.md"),
]

MANDATORY_CHECKS = """\
Run these commands IN ORDER from the `backend/` directory.
Record the exact output of each. Do not paraphrase.

```bash
cd backend

# Step 1 — Lint (must exit 0 before proceeding)
ruff check app tests

# Step 2 — Type check (advisory; log output, continue on warnings)
mypy app --ignore-missing-imports --no-strict-optional

# Step 3 — Tests (must exit 0; count must meet minimum stated in task)
pytest tests/ -q
```

Fix any ruff error immediately before moving to the next file.
Do not defer lint fixes to the end."""

STOP_CONDITIONS = """\
These are absolute. Violating any one is a critical failure — stop and report it.

1. DO NOT run `git commit` for any reason. Akhil commits.
2. DO NOT run `git push` for any reason.
3. DO NOT modify any file not listed under "Files Allowed to Change" in the task.
4. DO NOT upgrade or add packages not explicitly named in the task's "Implementation Notes".
5. DO NOT start a second task or begin the next phase.
6. DO NOT report success if ruff or pytest exits non-zero.
7. DO NOT remove, comment out, or weaken any existing test.
8. DO NOT leave a file above 500 lines. Surface the conflict before implementing."""

EXPECTED_OUTPUT = """\
Produce a structured report with these exact sections when implementation is complete:

### 1. Diff Summary
For every file changed: filename, lines added (+N), lines removed (-N).

### 2. Mandatory Check Results
Paste the literal terminal output for ruff, mypy, and pytest.
Label each block with the command that produced it.

### 3. Test Delta
List every new test function by name with a one-line description of what it covers.

### 4. Acceptance Criteria Status
Re-state each numbered criterion from the task file.
Mark each: PASS or FAIL. If FAIL, state exactly what is missing or broken.

### 5. Handoff
If all criteria are PASS: write "Implementation complete. Ready for QA Agent."
If any criterion is FAIL: write "Blocked on: [criterion]. Stopping." Do not proceed."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load(path: Path, label: str) -> str:
    if not path.exists():
        sys.exit(f"ERROR: Required file not found: {path}\n"
                 f"       ({label})\n"
                 f"       Run from the repo root or verify the file exists.")
    return path.read_text(encoding="utf-8").rstrip()


def _section(title: str, body: str) -> str:
    bar = "─" * 72
    return f"\n\n{bar}\n## {title}\n{bar}\n\n{body}"


def _doc_block(label: str, content: str) -> str:
    return f"### {label}\n\n{content}"


# ── Prompt builder ────────────────────────────────────────────────────────────

def build_prompt(task_path: Path) -> str:
    task_content = _load(task_path, "task file")

    doc_blocks: list[str] = []
    for label, path in REQUIRED_DOCS:
        doc_blocks.append(_doc_block(label, _load(path, label)))

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    task_rel = task_path.relative_to(REPO_ROOT) if task_path.is_absolute() else task_path

    header = f"""\
# Implementation Agent Prompt
Generated : {timestamp}
Task file : {task_rel}
Repo root : {REPO_ROOT}

---

## Your Role

You are the **Implementation Agent** for the FIFA 2026 Intelligence Platform.

Your job is to implement exactly what the task below describes — nothing more, nothing less.
You start every session by reading the project docs embedded in this prompt.
After implementation you run mandatory checks and produce a structured report.

The hard rules in AGENTS.md all apply. Read that section before writing any code."""

    sections = [
        header,
        _section(
            "PROJECT CONTEXT  (read before writing any code)",
            "\n\n".join(doc_blocks),
        ),
        _section("TASK", task_content),
        _section("MANDATORY CHECKS", MANDATORY_CHECKS),
        _section("STOP CONDITIONS", STOP_CONDITIONS),
        _section("EXPECTED OUTPUT FORMAT", EXPECTED_OUTPUT),
    ]

    return "\n".join(sections) + "\n"


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an implementation prompt from a task file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("task", help="Path to the task markdown file (e.g. tasks/phase_4b_redis_checkpointing.md)")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write prompt to FILE instead of stdout")
    args = parser.parse_args()

    task_path = Path(args.task)
    if not task_path.is_absolute():
        # Try relative to CWD first, then repo root
        if not task_path.exists():
            task_path = REPO_ROOT / args.task

    prompt = build_prompt(task_path)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(prompt, encoding="utf-8")
        print(f"Prompt written to {out}  ({len(prompt):,} chars)", file=sys.stderr)
    else:
        sys.stdout.write(prompt)


if __name__ == "__main__":
    main()

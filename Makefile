TASK ?= tasks/phase_4b_redis_checkpointing.md

.PHONY: agent-task check help

## Generate an implementation prompt from a task file and print to stdout.
## Usage: make agent-task TASK=tasks/phase_4b_redis_checkpointing.md
agent-task:
	python scripts/agent_task_runner.py $(TASK)

## Run the mandatory checks (ruff + mypy + pytest) from backend/.
## This is the same sequence the Implementation Agent must run before reporting done.
check:
	cd backend && ruff check app tests
	cd backend && mypy app --ignore-missing-imports --no-strict-optional
	cd backend && pytest tests/ -q

help:
	@echo ""
	@echo "FIFA 2026 Platform — Agent Automation"
	@echo ""
	@echo "  make agent-task [TASK=<path>]   Build implementation prompt from task file"
	@echo "  make check                       Run ruff + mypy + pytest (backend/)"
	@echo "  make help                        Show this message"
	@echo ""
	@echo "Default TASK: $(TASK)"
	@echo ""
	@echo "Examples:"
	@echo "  make agent-task"
	@echo "  make agent-task TASK=tasks/phase_4b_redis_checkpointing.md"
	@echo "  make agent-task TASK=tasks/phase_4b_redis_checkpointing.md | pbcopy"
	@echo "  make agent-task TASK=tasks/phase_4b_redis_checkpointing.md --output /tmp/prompt.md"
	@echo ""
	@echo "See docs/AGENT_RUNBOOK.md for full usage instructions."

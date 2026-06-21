# Task: Phase 6A — Observability / LangSmith

**Phase:** 6A  
**Roadmap goal:** Production-grade tracing and monitoring — trace every `run_query` call end-to-end through LangGraph via LangSmith.  
**Stable tag at task creation:** `phase-4b-redis-checkpointing-stable`  
**Branch:** `phase-6a-observability-langsmith`  
**Test baseline:** 128 tests passing (see `docs/PROJECT_STATE.md`)  
**Minimum tests after merge:** 133 (128 existing + 5 new)

---

## Goal

The platform has no end-to-end trace visibility. When a chat request fails or produces a
poor response, there is no way to inspect which nodes executed, what inputs they received,
or what intermediate state looked like. Structured `AgentTrace` entries exist per-node but
are written only to PostgreSQL — they are not visible in a live trace UI.

This task wires LangSmith tracing into the LangGraph pipeline. After implementation,
every `run_query()` invocation will produce a run tree in LangSmith showing each node,
its inputs/outputs, and latency. The analyst's LLM call will appear as a child span.

When LangSmith environment variables are absent (CI, local without a key), all behavior is
identical to today — tracing silently does nothing. The application must start and all tests
must pass without any LangSmith credentials.

**Phoenix / Arize** RAG evaluation visibility is explicitly **out of scope** for this phase.
**Custom Prometheus metrics** beyond what `prometheus-fastapi-instrumentator` already captures
are explicitly **out of scope** for this phase.

---

## Scope

**In scope:**
- Add `langsmith>=0.1.77` to `requirements.txt`
- Add four LangSmith settings to `app/core/config.py` with safe defaults
- Instrument `run_query()` in `orchestrator.py` with `@traceable` from `langsmith`
- Instrument the LLM call in `app/core/llm.py` with `@traceable` so LLM spans appear
  as child runs under the `run_query` root trace
- Add a startup log line in `app/main.py` lifespan confirming whether tracing is enabled
  or skipped (no connectivity check — just log the configured state)
- Write 5 new tests covering the tracing-enabled/disabled paths
- Update `docs/PROJECT_STATE.md` when implementation is complete
- Record any new technical debt in `docs/DECISIONS.md`

**Out of scope (do not touch):**
- Phoenix / Arize integration
- Custom Prometheus counters or histograms
- The streaming path (`event_generator` in `chat.py`) — streaming nodes are chained
  manually, not via LangGraph; tracing the streaming path is a separate follow-up
- Any agent file except `orchestrator.py` and `llm.py`
- ChromaDB, prediction, simulation, research, stats agent files
- Alembic migrations
- Docker Compose / infra files
- CI workflow (LangSmith key is not available in CI; tests must pass without it)
- Frontend

---

## Files Allowed to Change

```
backend/requirements.txt
backend/app/core/config.py
backend/app/core/llm.py
backend/app/agents/orchestrator.py
backend/app/main.py
backend/tests/test_agents/test_orchestrator.py
docs/PROJECT_STATE.md
docs/DECISIONS.md
```

No other file may be touched. If you discover a required change outside this list,
stop and surface the conflict. Do not proceed.

---

## Files Not Allowed to Change

```
backend/app/agents/analyst_agent.py
backend/app/agents/prediction_agent.py
backend/app/agents/research_agent.py
backend/app/agents/simulation_agent.py
backend/app/agents/stats_agent.py
backend/app/agents/state.py
backend/app/api/v1/chat.py
backend/app/api/v1/health.py
backend/app/api/v1/auth.py
backend/app/api/v1/teams.py
backend/app/api/v1/matches.py
backend/app/api/v1/predictions.py
backend/app/api/v1/simulation.py
backend/app/db/
backend/app/schemas/
backend/app/ml/
backend/app/rag/
backend/tests/conftest.py
backend/tests/test_api/
infra/
.github/workflows/ci.yml
frontend/
```

---

## Acceptance Criteria

Each criterion must be independently verifiable. The QA Agent will check each one.

1. `ruff check app tests` exits 0 from `backend/`.
2. `pytest tests/ -q` exits 0 from `backend/` with count ≥ 133.
3. All 128 pre-existing tests still pass — no test removed, weakened, or changed.
4. When `LANGCHAIN_TRACING_V2` is unset or `LANGCHAIN_API_KEY` is unset, `run_query()`
   runs to completion without error and produces the same result as today. Verified by
   the full existing test suite passing without any LangSmith env vars set.
5. `run_query()` in `orchestrator.py` is decorated with `@traceable`. The decorator must
   be applied at function definition, not at call site.
6. The LLM call function in `app/core/llm.py` is decorated with `@traceable`. When
   `LANGCHAIN_TRACING_V2=true` and a valid API key is set, the LLM span appears as a
   child of the `run_query` root trace. Verified structurally (decorator present); live
   LangSmith connectivity is not verified in CI.
7. `app/core/config.py` exposes `langsmith_tracing_enabled: bool`, `langsmith_api_key`,
   `langsmith_project`, and `langsmith_endpoint` settings with defaults that disable
   tracing when env vars are absent.
8. `app/main.py` lifespan logs whether LangSmith tracing is enabled or disabled at startup
   (structlog, level `info`). It does not attempt a network connection to LangSmith —
   log only.
9. No `LANGCHAIN_API_KEY` value appears in any committed file. The key is read exclusively
   from the environment at runtime via `config.py`.
10. `docs/PROJECT_STATE.md` updated to reflect Phase 6A completion.
11. Any new technical debt introduced is recorded in `docs/DECISIONS.md`.

---

## Required Tests

Write these 5 test functions in `tests/test_agents/test_orchestrator.py`. Names are
prescriptive — use them exactly.

| Function | What it must verify |
|---|---|
| `test_run_query_completes_without_langsmith_env_vars` | With `LANGCHAIN_TRACING_V2` and `LANGCHAIN_API_KEY` unset (use `monkeypatch.delenv` with `raising=False`), assert `run_query("who wins Brazil vs Argentina")` returns a dict with a `"response"` key and does not raise. Uses mocked graph (monkeypatch `_graph_fallback`). |
| `test_run_query_is_decorated_with_traceable` | Import `run_query` from `app.agents.orchestrator`; assert `hasattr(run_query, "__wrapped__")` or that the `langsmith` `traceable` wrapper is present — without calling the function. |
| `test_llm_function_is_decorated_with_traceable` | Import the LLM call function from `app.core.llm`; assert it carries the `@traceable` wrapper. |
| `test_settings_langsmith_tracing_disabled_by_default` | Instantiate `Settings()` with no LangSmith env vars set; assert `settings.langsmith_tracing_enabled` is `False` and `settings.langsmith_api_key` is `None` or empty string. |
| `test_settings_langsmith_tracing_enabled_when_env_vars_set` | Use `monkeypatch.setenv` to set `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY=test-key`, `LANGCHAIN_PROJECT=test-project`; instantiate `Settings()`; assert `langsmith_tracing_enabled` is `True` and `langsmith_project == "test-project"`. |

**Pattern note:** Follow the existing patch-at-module-origin pattern from `docs/DECISIONS.md`.
No live LangSmith API calls in any test. No test may set `LANGCHAIN_API_KEY` to a real key.

---

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `LANGCHAIN_TRACING_V2` | No | `"false"` | LangChain/LangSmith standard flag; `"true"` enables tracing |
| `LANGCHAIN_API_KEY` | No | `""` | LangSmith API key — **never commit this value** |
| `LANGCHAIN_PROJECT` | No | `"fifa2026-platform"` | LangSmith project name; traces group under this project |
| `LANGCHAIN_ENDPOINT` | No | `"https://api.smith.langchain.com"` | LangSmith ingestion endpoint; change only for self-hosted |

**Local setup:** Add all four to `.env` (git-ignored). Do not add to `.env.example` with
real values — use placeholder comments only.

**CI:** None of these variables are set in GitHub Actions. All tests must pass without them.
The `LANGCHAIN_API_KEY` must never appear in `.github/workflows/ci.yml`.

---

## Security Concerns

1. **`LANGCHAIN_API_KEY` is a secret.** It must be read exclusively from the environment.
   Never hardcode it, log it, or include it in any response body or trace metadata.
   The `config.py` field must use `pydantic_settings` secret handling (type `str`, default
   `""`) — do not use `SecretStr` unless it is already used elsewhere in `config.py`
   (check first; do not introduce a new pattern inconsistently).

2. **Query content and agent traces are sent to LangSmith.** When tracing is enabled,
   user queries and agent outputs are transmitted to Langchain's servers. This is acceptable
   for a development/portfolio deployment but must be noted as a data-handling concern in
   `docs/DECISIONS.md` before production use. Add a TD entry.

3. **No PII scrubbing is required in this phase.** The platform handles football queries
   only. PII exposure risk is low. If user authentication (Phase 4C) adds user-identifying
   data to `PlatformState`, a follow-up phase must review what LangSmith receives.

4. **Graceful degradation is mandatory.** A failed LangSmith connection (network error,
   invalid key, rate limit) must never raise an unhandled exception in `run_query()`.
   The `@traceable` decorator from the `langsmith` package handles this automatically
   when tracing is disabled. Verify this behavior with the
   `test_run_query_completes_without_langsmith_env_vars` test.

---

## Fallback Behavior When LangSmith Env Vars Are Missing

LangSmith tracing uses the LangChain standard environment variable `LANGCHAIN_TRACING_V2`.
When this variable is absent or set to any value other than `"true"`, the `langsmith`
library's `@traceable` decorator is a transparent passthrough — it calls the wrapped
function directly with zero overhead and no network I/O.

The implementation must rely on this built-in behavior:

1. **`app/core/config.py`:** `langsmith_tracing_enabled` derives from
   `LANGCHAIN_TRACING_V2` — `True` only when the env var is literally `"true"`.
   All other values (absent, `"false"`, `"1"`) → `False`.

2. **`app/main.py` lifespan:** Read `settings.langsmith_tracing_enabled`. Log at `info`
   level: either `"langsmith.tracing.enabled"` (with project name) or
   `"langsmith.tracing.disabled"`. No connection attempt. No exception path needed.

3. **`run_query()` in `orchestrator.py`:** The `@traceable` decorator handles the
   enabled/disabled branching internally. No `if tracing_enabled` guard is needed in
   the function body.

4. **`llm.py`:** Same pattern. `@traceable` wraps the LLM call function. No conditional.

This means the entire fallback behavior is provided by the `langsmith` package itself —
no custom try/except is needed around the tracing path. This is the correct, low-maintenance
approach. **Do not** write a manual `try: langsmith_client.create_run(...)` pattern.

---

## Implementation Notes

### Install order (do this first, in isolation)

Add `langsmith>=0.1.77` to `requirements.txt` under the `# Phase 2 — Agents & ML` section,
then run `pip install --dry-run -r requirements.txt` to confirm no conflicts.
Then run `pytest tests/ -q` immediately — all 128 tests must pass before any code changes.

Check that `langsmith>=0.1.77` does not conflict with the `langchain-core>=0.3.0` pin
introduced in Phase 4B. Verify with:
```bash
pip install --dry-run langsmith langchain-core
```

### config.py changes

Add to `Settings` in `app/core/config.py`:
```python
langsmith_tracing_enabled: bool = False
langsmith_api_key: str = ""
langsmith_project: str = "fifa2026-platform"
langsmith_endpoint: str = "https://api.smith.langchain.com"
```

Map `langsmith_tracing_enabled` from the `LANGCHAIN_TRACING_V2` env var. Pydantic-settings
handles boolean env var parsing automatically when the field type is `bool` and the env
var name is set via `model_config` or `AliasChoices`. Check how existing boolean fields
in `config.py` are handled before writing this — match the existing pattern.

### orchestrator.py changes

Current `run_query()` is at approximately line 140 in `orchestrator.py` (203 lines total).
The file must stay under 500 lines after this change. The `@traceable` decorator import and
application add ~3 lines. No risk of exceeding the limit.

```python
from langsmith import traceable

@traceable(name="run_query", run_type="chain")
async def run_query(
    query: str,
    extra_state: Dict[str, Any] | None = None,
    thread_id: str | None = None,
) -> PlatformState:
    ...
```

The `run_type="chain"` designation tells LangSmith this is an orchestration step, not an
LLM call. Do not change the function body.

### llm.py changes

`app/core/llm.py` contains the LLM call that the analyst agent uses (160 lines). Identify
the function that makes the OpenAI `client.chat.completions.create` call (or the streaming
variant). Apply `@traceable(name="analyst_llm", run_type="llm")` to that function.

If both a streaming and non-streaming variant exist, apply `@traceable` to both.

The `run_type="llm"` designation makes the span appear as an LLM span in LangSmith's trace
UI, enabling token count and latency visibility.

### main.py lifespan change

The `lifespan` async context manager in `main.py` (78 lines) already handles Redis
initialization. Add LangSmith status logging after the Redis block, before `yield`:

```python
if settings.langsmith_tracing_enabled:
    log.info("langsmith.tracing.enabled", project=settings.langsmith_project)
else:
    log.info("langsmith.tracing.disabled")
```

No import of `langsmith.Client`. No connection attempt. Log only.

### line count check (mandatory before declaring complete)

After all changes, run:
```bash
wc -l backend/app/agents/orchestrator.py backend/app/core/llm.py \
   backend/app/core/config.py backend/app/main.py
```

No file may exceed 500 lines. The current counts are:
- `orchestrator.py`: 203 lines
- `llm.py`: 160 lines
- `config.py`: 61 lines
- `main.py`: 78 lines

---

## Documentation Updates Required

### `docs/PROJECT_STATE.md`

1. Add a row to the Core Infrastructure table:
   ```
   | LangSmith tracing | ✅ Active (when LANGCHAIN_TRACING_V2=true) | `@traceable` on `run_query` and LLM call; no-op when env vars absent |
   ```
2. Update the test count from `128` to the final count after this phase.
3. Update the test table rows for `test_orchestrator.py` (5 new tests → new total).
4. Update "Last phase completed" to `Phase 6A` and update the date.

### `docs/DECISIONS.md`

Add two entries to the Known Technical Debt Summary table:

| ID | Item | Severity | Phase to fix |
|---|---|---|---|
| TD-11 | LangSmith receives full query content and agent outputs; no PII scrubbing in place | Low | Revisit before public deployment; low risk for football-only queries |
| TD-12 | Streaming path (`event_generator`) is not traced; manual node chain has no LangSmith visibility | Low | Phase 6B — requires wrapping each node call with `@traceable` or switching to LangGraph native streaming |

Also add a decision record:

**Decision: `@traceable` decorator over explicit `RunTree` API**

**Chosen:** `langsmith.traceable` decorator on `run_query` and the LLM function.

**Why:** The decorator approach requires zero changes to function signatures and handles
the enabled/disabled branching internally. The alternative (`RunTree` manual API) requires
wrapping every call site with try/except and managing parent/child span IDs explicitly —
that is high coupling for an observability concern.

**Trade-off:** The decorator traces only the two instrumented functions. Intermediate
LangGraph node spans (orchestrator_node, stats_node, etc.) will not appear as separate
child spans in LangSmith unless each node is individually decorated. Full per-node
visibility requires either decorating each node function or switching the analyst to
use `langchain_openai.ChatOpenAI` (which auto-instruments). Deferred to Phase 6B.

---

## Rollback Notes

**Stable tag to restore if this branch breaks `main`:** `phase-4b-redis-checkpointing-stable`

```bash
git checkout phase-4b-redis-checkpointing-stable
```

The broken branch stays for post-mortem. The `langsmith` package addition (requirements.txt
change) is the highest-risk step — isolate it and verify 128/128 tests pass before
modifying any Python source file. If the package addition alone causes a dependency
conflict, stop and report before touching any `.py` file.

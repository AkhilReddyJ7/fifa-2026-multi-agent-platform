# Task: Phase 4B — LangGraph Checkpointing with Redis

**Phase:** 4B  
**Roadmap goal:** Persist graph state across requests for true multi-turn agent memory.  
**Stable tag at task creation:** `phase-4c-auth-stable`  
**Branch:** `phase-4b-redis-checkpointing`  
**Test baseline:** 109 tests passing (see `docs/PROJECT_STATE.md`)  
**Minimum tests after merge:** 116 (109 existing + 7 new)

---

## Goal

The LangGraph graph is currently compiled without a checkpointer (`g.compile()` in
`backend/app/agents/orchestrator.py:155`). Every call to `run_query()` starts from
a blank `PlatformState` — agent reasoning from prior turns is discarded.

This task wires `AsyncRedisSaver` as the LangGraph checkpointer for the non-streaming
chat path. After implementation, the `chat()` endpoint will pass the session UUID as
the `thread_id`, and LangGraph will persist the full graph state in Redis between turns.
A graceful fallback to stateless execution handles Redis unavailability.

The streaming path (`event_generator` in `chat.py`) is explicitly **out of scope**.
It does not use the LangGraph graph and will not be checkpointed in this phase.

---

## Scope

**In scope:**
- Upgrade `langgraph` from `0.2.28` to `>=1.2.0,<2.0.0`
- Add `langgraph-checkpoint>=4.0.0` to `requirements.txt`
- Add `langgraph-checkpoint-redis>=1.0.0` to `requirements.txt`
- Upgrade `langchain-core` from `0.2.39` to `>=0.3.0` (required by langgraph 1.x)
- Add `redis_checkpoint_url` setting to `config.py`
- Modify `build_graph()` to accept an optional `checkpointer` parameter
- Add `AsyncRedisSaver` initialization in `main.py` application lifespan
- Modify `run_query()` to accept `thread_id: str | None` and pass `config` to `ainvoke`
- Wire `session.session_uuid` as `thread_id` in the `chat()` endpoint
- Add `MemorySaver` fixture to `conftest.py` for test-time use
- Write 7 new tests covering: `thread_id` pass-through, fallback, MemorySaver multi-turn
- Update `docs/PROJECT_STATE.md` when implementation is complete

**Out of scope (do not touch):**
- The streaming path (`event_generator` in `chat.py`)
- Any agent file (`orchestrator.py` graph construction logic beyond `build_graph`)
- ChromaDB, prediction, simulation, research, stats agent files
- Alembic migrations (no DB schema changes)
- Docker Compose / infra files
- CI workflow (Redis service container addition is a separate follow-up)
- Frontend

---

## Files Allowed to Change

```
backend/requirements.txt
backend/app/core/config.py
backend/app/agents/orchestrator.py
backend/app/main.py
backend/app/api/v1/chat.py
backend/tests/conftest.py
backend/tests/test_agents/test_orchestrator.py
backend/tests/test_api/test_chat.py
docs/PROJECT_STATE.md
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
backend/app/db/
backend/app/schemas/
backend/app/api/v1/health.py
backend/app/api/v1/auth.py
backend/app/api/v1/teams.py
backend/app/api/v1/matches.py
backend/app/api/v1/predictions.py
backend/app/api/v1/simulation.py
backend/app/ml/
backend/app/rag/
infra/
.github/workflows/ci.yml
frontend/
```

---

## Acceptance Criteria

Each criterion must be independently verifiable. The QA Agent will check each one.

1. `ruff check app tests` exits 0 from `backend/`.
2. `pytest tests/ -q` exits 0 from `backend/` with count ≥ 116.
3. All 109 pre-existing tests still pass — no test removed, weakened, or changed to a mock when it was previously an integration.
4. `run_query()` accepts `thread_id: str | None = None`. When provided and Redis is reachable, `graph.ainvoke()` is called with `config={"configurable": {"thread_id": thread_id}}`. Verified by unit test.
5. When `thread_id` is `None` or the checkpointer is unavailable, `run_query()` falls back to stateless `ainvoke()` with no `config`. Verified by unit test that simulates a `RedisError`.
6. The `chat()` endpoint (non-streaming POST) passes `thread_id=session.session_uuid` to `run_query()`. Verified by API-level test.
7. The streaming `chat_stream_endpoint` is unchanged — no new `thread_id` argument, no checkpointer reference. Verified by reading the function and confirming the existing 3 streaming tests still pass.
8. `docs/PROJECT_STATE.md` Redis row updated from "⚠️ Configured only" to reflect active use.
9. Any new technical debt introduced is recorded in `docs/DECISIONS.md` under "Known Technical Debt Summary" before implementation is declared complete.

---

## Mandatory Tests

Write these 7 test functions. Names are prescriptive — use them exactly.

**In `tests/test_agents/test_orchestrator.py`:**

| Function | What it must verify |
|---|---|
| `test_run_query_with_thread_id_passes_config_to_ainvoke` | Monkeypatch `graph.ainvoke`; assert it was called with `config={"configurable": {"thread_id": "test-uuid-123"}}` |
| `test_run_query_without_thread_id_is_stateless` | Monkeypatch `graph.ainvoke`; assert it was called with no `config` keyword argument (or `config=None`) |
| `test_build_graph_with_memory_saver_compiles` | Pass a `MemorySaver()` to `build_graph(checkpointer=...)`; assert the result is not None and does not raise |
| `test_run_query_falls_back_on_redis_error` | Patch `ainvoke` on `_graph_checkpointed` to raise `redis.exceptions.ConnectionError`; assert `run_query` completes using the fallback graph |

**In `tests/test_api/test_chat.py`:**

| Function | What it must verify |
|---|---|
| `test_chat_endpoint_passes_session_uuid_as_thread_id` | Monkeypatch `run_query`; call `POST /api/v1/chat`; assert `run_query` was called with `thread_id` equal to the session UUID returned in the response |
| `test_chat_stream_endpoint_does_not_pass_thread_id` | Monkeypatch `run_query`; call `POST /api/v1/chat/stream`; assert `run_query` was NOT called (streaming path uses manual node chain, not `run_query`) |
| `test_multiturn_memory_with_memory_saver` | Use `MemorySaver` fixture; call `run_query` twice with the same `thread_id`; assert the second call's result state includes `history` that references the first call's query or response |

**Pattern note:** Tests use `MemorySaver` from `langgraph.checkpoint.memory` instead of `AsyncRedisSaver`.
No Redis service is required in CI. Follow the existing patch-at-module-origin pattern documented in `docs/DECISIONS.md`.

---

## Implementation Notes

### LangGraph version upgrade (do this first, in isolation)

Before writing any checkpoint code, upgrade the packages:
```
langgraph>=1.2.0,<2.0.0          # was 0.2.28
langgraph-checkpoint>=4.0.0       # new
langgraph-checkpoint-redis>=1.0.0 # new
langchain-core>=0.3.0             # was 0.2.39
```

After the requirements change, run `pytest tests/ -q` immediately. All 109 tests
must pass before writing any new code. The LangGraph 1.x graph compilation API is
backward-compatible with 0.2.x for this codebase — no node signatures change.

### New config key

Add to `Settings` in `app/core/config.py`:
```python
redis_checkpoint_url: str = "redis://localhost:6379/1"
```

Use DB 1 (not DB 0) to isolate checkpoints from any future caching on the default DB.

### Checkpointer initialization (main.py lifespan)

Use the `lifespan` async context manager already in `main.py`. On startup:
```python
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
saver = await AsyncRedisSaver.from_conn_string(settings.redis_checkpoint_url)
# store on app.state or pass to orchestrator module initializer
```
If the connection fails, log a warning and continue — do not prevent startup.

### build_graph signature change (orchestrator.py)

```python
def build_graph(checkpointer=None) -> Any:
    ...
    return g.compile(checkpointer=checkpointer)
```

Keep two module-level graph singletons:
- `_graph_fallback` — compiled without checkpointer, always available
- `_graph_checkpointed` — compiled with `AsyncRedisSaver`, set only when Redis is up

### run_query signature change (orchestrator.py)

```python
async def run_query(
    query: str,
    extra_state: Dict[str, Any] | None = None,
    thread_id: str | None = None,
) -> PlatformState:
```

Logic:
1. Build `state = initial_state(query)` + apply `extra_state`
2. If `thread_id` is not None and `_graph_checkpointed` is not None:
   - Call `_graph_checkpointed.ainvoke(state, config={"configurable": {"thread_id": thread_id}})`
   - On `redis.exceptions.RedisError`: log warning, fall back to step 3
3. Else: call `_graph_fallback.ainvoke(state)`

### operator.add trace accumulation (known trade-off)

`PlatformState.trace` uses `Annotated[List[AgentTrace], operator.add]`. With checkpointing
active, `result["trace"]` on turn 2 will contain turn 1's traces plus turn 2's traces.

**Accept this in Phase 4B.** Record it as TD-10 in `docs/DECISIONS.md`:
> TD-10: With Redis checkpointing active, `PlatformState.trace` accumulates across all turns
> for a session. `ChatMessage.agent_trace` grows with session length. Fix: slice to current-turn
> traces only using pre-invocation checkpoint count. Deferred to Phase 5+.

### Streaming path

The `event_generator()` function in `chat.py` does not use `run_query()` or the LangGraph
graph. It manually chains nodes. It must not be modified in this phase. The existing 3
streaming tests (`test_stream_*`) must continue to pass without change.

---

## Rollback Notes

**Stable tag to restore if this branch breaks `main`:** `phase-4c-auth-stable`

```bash
git checkout phase-4c-auth-stable
```

The broken branch stays for post-mortem. The LangGraph upgrade (requirements.txt change)
is the highest-risk step — isolate it and verify 109/109 tests pass before proceeding
to any other change. If the upgrade alone causes failures, stop and report before touching
any Python source file.

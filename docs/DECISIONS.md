# Technical Decisions — FIFA 2026 Intelligence Platform

Architecture decisions, trade-offs, and known technical debt recorded for future contributors.

---

## Agent Orchestration

### Decision: LangGraph StateGraph over raw async chains

**Chosen:** LangGraph `StateGraph` with `PlatformState` TypedDict, conditional edges, and `operator.add` trace accumulation.

**Why:** Conditional routing between prediction, simulation, and research nodes is a first-class graph operation in LangGraph. The `operator.add` annotation on `trace` accumulates agent traces automatically across all nodes without explicit merge code. Checkpointing (Phase 4B) plugs in without restructuring the graph.

**Trade-off:** LangGraph was upgraded from `0.2.28` to `>=1.2.0,<2.0.0` in Phase 4B. The `AsyncRedisSaver` is from `langgraph-checkpoint-redis` (latest available: `0.4.x`, not `1.0.x` as originally planned — no `1.0.x` release exists on PyPI). The compile API is backward-compatible.

---

### Decision: Manual node chaining in streaming path

**Chosen:** `event_generator()` in `chat.py` manually calls `orchestrator_node → stats_node → [simulation/prediction_node] → research_node → analyst_stream`, mirroring the `_route_after_stats` logic.

**Why:** LangGraph's `ainvoke` returns the final state all at once — it does not expose per-node yields. SSE streaming requires chunk-by-chunk output from `analyst_stream`. The manual chain is necessary to support streaming while preserving the same routing logic.

**Debt:** The routing logic is duplicated between `orchestrator.py` (`_route_after_stats`) and `chat.py` (`event_generator`). If routing rules change, both must be updated. The Phase 4A-Lite fix addressed the specific bug where `simulation_node` was missing from the streaming path.

---

### Decision: Regex intent classification

**Chosen:** Regex patterns for intent detection; no LLM call in the orchestrator.

**Why:** Deterministic, zero-latency, testable (16 orchestrator tests run in <1ms). For a constrained domain (5 intents, football-specific vocabulary) regex is sufficient and avoids a round-trip LLM call on every request.

**Trade-off:** The regex vocabulary must be maintained manually. Ambiguous queries (e.g., "How strong is Brazil?" — analyze or lookup?) fall to the default `chat` intent and produce a generic response instead of routing to the stats agent.

---

## Prediction Model

### Decision: ELO-Poisson with no ML training required

**Chosen:** ELO expected score mapped to Poisson expected goals; Dixon-Coles-inspired score probability matrix (`app/ml/predictor.py`).

**Why:** ELO ratings are the standard for football strength estimation and are available for all 48 teams. The model requires no training data, no scikit-learn dependency, and is fully deterministic. It runs in <1ms with zero I/O.

**Trade-off:** The model uses only ELO rating and form index. It ignores squad composition, injury lists, tactical matchups, altitude, and weather. For a portfolio project this is appropriate; for production prediction a gradient-boosted model on tabular features would outperform it significantly.

**Model version string:** `"elo-poisson-v1"` stored in `predictions.model_version`.

---

## Simulation

### Decision: asyncio.to_thread for Monte Carlo

**Chosen:** `await asyncio.to_thread(run_simulation, ...)` in `simulation_node`.

**Why:** `run_simulation` is a pure Python CPU loop simulating thousands of tournament brackets. Calling it directly inside an `async def` blocks the event loop for the duration of the simulation, preventing any other requests from being processed. `asyncio.to_thread` offloads the CPU work to the thread pool executor.

**Alternative considered:** Moving `simulation_node` to a background task (Celery, ARQ). Rejected for Phase 4A-Lite — adds infrastructure complexity without benefit for a single-node deployment.

**When this breaks:** Under concurrent load, multiple simultaneous `/simulation` requests each spawn a thread. The default Python `ThreadPoolExecutor` caps at `min(32, os.cpu_count() + 4)` threads. Under high concurrency, requests queue behind the thread pool limit. A worker queue (Redis + ARQ) would be the correct fix for production.

---

## RAG Architecture

### Decision: Three dedicated collections with intent-aware queries

**Chosen:** Separate ChromaDB collections for `world_cup_history`, `team_profiles`, and `match_reports`, each queried with a different query string tuned for that collection's content.

**Why:** A single query against a mixed collection produces unbalanced retrieval — one document type dominates depending on the query. Intent-aware query construction and per-collection `n_results` budgets (e.g., `predict` → more match reports, `simulate` → more history) give the analyst more relevant, balanced context.

**Debt:** Metadata stored in ChromaDB (team codes, year, stage) is never used as a filter — all retrieval is semantic. Adding `where` clause filtering (e.g., only retrieve documents where `team_code == "BRA"`) is Phase 5B work and would improve precision significantly.

---

### Decision: Synchronous ChromaDB client

**Chosen:** `chromadb.HttpClient` (synchronous) in an async application.

**Why:** ChromaDB's `AsyncHttpClient` was not stable at the time of development (ChromaDB 0.5.3). The synchronous client is the documented production path.

**Debt:** Every call to `search_wc_history`, `search_team_profiles`, or `search_match_reports` blocks the asyncio event loop for the duration of the HTTP round-trip to ChromaDB. Under load this degrades responsiveness. The fix is `asyncio.to_thread(col.query, ...)` (same pattern as the simulation fix) until an official async client is available.

---

## Database

### Decision: Async SQLAlchemy with request-scoped sessions

**Chosen:** `get_db()` dependency yields a single `AsyncSession` per request; commits on exit, rolls back on exception.

**Why:** SQLAlchemy 2.x async session is the standard pattern for FastAPI + PostgreSQL. Session-scoped transactions allow `db.flush()` to make data visible within a request without committing until the handler succeeds.

**Exception:** `stats_node` creates its own `AsyncSessionLocal()` session directly (bypasses FastAPI DI). This is intentional — the agent pipeline runs via `run_query()` which has no HTTP context, so it cannot receive an injected session. The agent opens and closes its own session.

---

### Decision: SQLite in-memory for CI

**Chosen:** `DATABASE_URL=sqlite+aiosqlite:///:memory:` in GitHub Actions; no external services.

**Why:** Eliminates the need for a PostgreSQL service container in CI, speeding up test runs and avoiding flaky service startup. SQLAlchemy's async abstraction makes the switch transparent for most queries.

**Constraints introduced:**
- `BigInteger` autoincrement is not used (SQLite maps it to `INTEGER` which lacks PostgreSQL's `BIGSERIAL` behavior in some edge cases — avoided by using `Integer` for `ChatMessage.id`)
- `pool_size` and `max_overflow` pool kwargs are incompatible with SQLite's `StaticPool`; detected via URL prefix and skipped
- `JSON` column type from `sqlalchemy.dialects.postgresql` is silently accepted by SQLite's any-type columns

---

## API Design

### Decision: HTTP 204 response class pattern

**Chosen:** `@router.delete(..., status_code=204, response_class=Response)` with `-> Response` return type and `return Response(status_code=204)`.

**Why:** FastAPI 0.111.1 calls `get_type_hints()` at route registration time. For `-> None`, Python returns `type(None)` which is truthy, causing FastAPI to set `response_model = NoneType` and then fail `assert is_body_allowed_for_status_code(204)` at import time. Returning an explicit `Response` object bypasses response model validation entirely.

**Note:** The `teams.py` router already used this pattern. The `chat.py` DELETE endpoint was fixed in the 204 CI investigation.

---

## Security

### Decision: JWT utilities written but not wired

**Chosen:** `app/core/security.py` has complete JWT encode/decode and bcrypt password hashing. No route is guarded.

**Why:** Authentication is correct to implement after the agent pipeline is stable — adding auth to broken routes adds debugging complexity. The utilities are ready to wire in Phase 4C.

**Risk:** The API is currently fully open. It should not be deployed to a public URL without Phase 4C.

---

## Testing

### Decision: Patch at module origin for locally-imported nodes

**Chosen:** Streaming tests patch `app.agents.orchestrator.orchestrator_node` (module origin), not `app.api.v1.chat.orchestrator_node`.

**Why:** Inside `event_generator()`, nodes are imported with `from app.agents.X import node_fn` at function call time. Python resolves this against the already-imported module in `sys.modules`. Patching the origin (`app.agents.X.node_fn`) replaces the value in the module namespace, which the local import then reads. Patching `app.api.v1.chat.node_fn` would fail because that name does not exist at module level.

**Exception:** `analyst_stream` is imported at the top of `chat.py` (`from app.agents.analyst_agent import analyst_stream`), so it IS available as `app.api.v1.chat.analyst_stream` and must be patched there.

---

## Observability

### Decision: `@traceable` decorator over explicit RunTree API

**Chosen:** `langsmith.traceable` decorator on `run_query` (orchestrator) and both LLM call functions (`chat_complete`, `chat_stream`) in `llm.py`.

**Why:** The decorator approach requires zero changes to function signatures and handles the enabled/disabled branching internally via `LANGCHAIN_TRACING_V2`. The alternative (manual `RunTree` API) requires wrapping every call site with try/except and managing parent/child span IDs explicitly — that is high coupling for an observability concern.

**Trade-off:** Only the two instrumented functions appear as traced spans. Intermediate LangGraph nodes (`orchestrator_node`, `stats_node`, etc.) do not appear as child spans unless individually decorated. Full per-node visibility requires either decorating each node function or switching the analyst to `langchain_openai.ChatOpenAI` (which auto-instruments). Deferred to Phase 6B as TD-12.

---

## Known Technical Debt Summary

| ID | Item | Severity | Phase to fix |
|----|------|----------|-------------|
| TD-1 | ChromaDB sync client blocks event loop | Medium | 5B |
| TD-2 | ~~Redis configured but unused~~ | ✅ Resolved | Phase 4B — `AsyncRedisSaver` checkpointer wired in non-streaming chat path |
| TD-3 | Auth not enforced; `user_id` always NULL | High | 4C |
| TD-4 | mypy `continue-on-error: true` in CI | Low | Ongoing |
| TD-5 | Routing logic duplicated between graph and streaming path | Medium | Refactor when routing complexity grows |
| TD-6 | No metadata filtering in RAG queries | Medium | 5B |
| TD-7 | Stats Agent opens its own DB session (not request-scoped) | Low | Acceptable for agent context; no fix needed |
| TD-8 | Chat table migrations not in Alembic | Low | Add migration before production deploy |
| TD-9 | Thread pool saturation under concurrent simulation load | Medium | 4B+ (worker queue) |
| TD-10 | `PlatformState.trace` accumulates across all turns when checkpointing is active; `ChatMessage.agent_trace` grows with session length | Low | 5+ (slice to current-turn traces only using pre-invocation checkpoint count) |
| TD-11 | LangSmith receives full query content and agent outputs; no PII scrubbing in place | Low | Revisit before public deployment; low risk for football-only queries |
| TD-12 | Streaming path (`event_generator`) is not traced; manual node chain has no LangSmith visibility | Low | Phase 6B — wrap each node call with `@traceable` or switch to LangGraph native streaming |

# Roadmap — FIFA 2026 Intelligence Platform

## Completed Phases

### Phase 1 — Foundation (commit `771deb7`)
**Goal:** Runnable API with full data model, seeding, and basic CRUD.

- FastAPI application skeleton with versioned router (`/api/v1`)
- PostgreSQL schema: `teams`, `players`, `matches`, `team_stats`
- Alembic migrations (migration `0001`)
- Full CRUD for Teams, Matches endpoints
- Docker Compose: Postgres + Redis + ChromaDB + API
- GitHub Actions CI (ruff → mypy → pytest → Docker build)
- Seed scripts for 48 FIFA 2026 teams and historical match data

### Phase 2 — Agent Pipeline (commit `771deb7`)
**Goal:** LangGraph multi-agent pipeline with intent routing and LLM synthesis.

- `PlatformState` TypedDict — shared state across all nodes
- `StateGraph` with conditional routing (`_route_after_stats`)
- **Orchestrator agent** — regex intent classification + team code extraction
- **Stats agent** — async PostgreSQL queries: team profiles, H2H, match stats
- **Prediction agent** — ELO-Poisson model; win/draw/loss probs + expected goals + XAI
- **Simulation agent** — Monte Carlo full-tournament simulator (48 teams, FIFA 2026 format)
- **Research agent** — ChromaDB RAG with intent-aware, collection-specific queries and interleaved results
- **Analyst agent** — LLM synthesis (GPT-4o) with local fallback; streaming support
- `/api/v1/predictions` and `/api/v1/simulation` endpoints (pipeline-backed)

### Phase 3A — RAG Content Pipeline (commit `19cf150`)
**Goal:** Populate ChromaDB with meaningful domain knowledge.

- Three JSON document corpora: `wc_history.json`, `team_profiles.json`, `match_reports.json`
- `app/rag/ingestion.py` — synchronous ingest functions for seed scripts
- `app/rag/chroma_client.py` — lazy `lru_cache` client, `get_or_create_collection`, cosine distance
- Intent-aware fetch sizes per collection in `research_agent.py`
- MD5-based cross-collection deduplication
- Round-robin interleaving of multi-collection results

### Phase 3B — Prediction and Simulation Persistence (commits `1a524b9`, `e4cbcad`)
**Goal:** All agent results stored in PostgreSQL for history and replay.

- `predictions` table and Alembic migration `0002`
- `simulation_runs` table in same migration
- `POST /api/v1/predictions` persists to `predictions` table; `GET /api/v1/predictions/{id}` retrieves
- `POST /api/v1/simulation` persists to `simulation_runs`; `GET /api/v1/simulation/{uuid}` retrieves
- API schema consistency fixes (Phase 3B.1)

### Phase 3C — Chat Session Persistence (commit `3ffe78e`)
**Goal:** Stateful chat with full message history.

- `chat_sessions` and `chat_messages` tables
- `POST /api/v1/chat` (non-streaming) — creates/resumes sessions, persists both turns
- `POST /api/v1/chat/stream` — SSE streaming with same persistence guarantees
- `GET /api/v1/chat/{uuid}` — full message history in chronological order
- `DELETE /api/v1/chat/{uuid}` — cascade delete
- History fed back into agent pipeline (last 10 messages as `history` in state)
- 10 chat API tests covering session lifecycle, persistence, history passing

### Phase 4A-Lite — Streaming Correctness and Async Safety (Phase 4A-Lite, 2026-06-11)
**Goal:** Ensure streaming and non-streaming paths are equivalent; eliminate event-loop blocking.

- **`simulation_agent.py`:** `asyncio.to_thread` wrapping of `run_simulation()` — Monte Carlo no longer blocks the event loop
- **`chat.py` streaming path:** Added `simulation_node` to `event_generator` local imports and `elif intent == "simulate":` branch — streaming now mirrors LangGraph graph routing exactly
- **`test_chat.py`:** 3 new streaming tests:
  - `test_stream_simulate_invokes_simulation_node` (regression test for the bug)
  - `test_stream_predict_does_not_invoke_simulation_node` (elif correctness)
  - `test_stream_returns_sse_and_persists_assistant_message` (SSE format + DB persistence)
- **204 fix:** `DELETE /api/v1/chat/{uuid}` changed to `-> Response` + `return Response(status_code=204)` to satisfy fastapi 0.111.1 `get_type_hints()` behavior
- Test suite: 109/109 passing

---

## Remaining Phases

### Phase 4B — LangGraph Checkpointing with Redis
**Goal:** Persist graph state across requests for true multi-turn agent memory.

- Replace stateless `graph.ainvoke` with `graph.ainvoke(..., config={"configurable": {"thread_id": session_uuid}})`
- Add `AsyncRedisSaver` checkpointer (LangGraph persistence API)
- Connect to existing Redis service (already in Docker Compose and `settings`)
- Chat sessions become resumable from any point; agent can reference prior reasoning
- **Files affected:** `app/agents/orchestrator.py`, `app/api/v1/chat.py`
- **Risk:** LangGraph checkpointer API changed between 0.1.x and 0.2.x; verify with pinned `langgraph==0.2.28`

### Phase 4C — Auth and User Identity
**Goal:** Gate the API with JWT authentication; link chat sessions to users.

- User registration and login endpoints (`POST /api/v1/auth/register`, `/login`)
- `users` table migration
- `user_id` on `ChatSession` populated from JWT subject
- FastAPI `Depends(get_current_user)` on all agent-backed endpoints
- **Files affected:** `app/core/security.py` (already complete), `app/api/v1/chat.py`, new `app/api/v1/auth.py`, new migration
- **Risk:** Low — `security.py` already has working JWT encode/decode and password hashing

### Phase 5A — Frontend (Next.js / React)
**Goal:** Web interface consuming all existing API endpoints.

- Chat interface with SSE streaming display
- Team browser (CRUD for teams and stats)
- Prediction comparison tool (two-team input → probabilities)
- Simulation dashboard (run + visualize tournament bracket)
- Requires: Phase 4C (auth) for session association; Phase 4B (checkpointing) optional but improves UX
- **Files affected:** `frontend/` (currently empty scaffold)

### Phase 5B — RAG Quality Improvements
**Goal:** Higher-precision retrieval without replacing the existing pipeline.

- Metadata filtering in `research_agent.py` using ChromaDB `where` clauses (e.g., filter by `year` range or `team_code`)
- Async ChromaDB client — switch from `chromadb.HttpClient` to async equivalent (pending ChromaDB API stability)
- Expand document corpora (more match reports, player-level documents)
- RAGAS evaluation harness for retrieval quality measurement
- **Files affected:** `app/agents/research_agent.py`, `app/rag/chroma_client.py`

### Phase 6A — Observability
**Goal:** Production-grade tracing and monitoring.

- LangSmith integration — trace every `run_query` call end-to-end through LangGraph
- Structured `agent_trace` already written per node; forward to LangSmith via callback
- Phoenix / Arize for RAG evaluation visibility
- Prometheus dashboard for API latency and error rates
- **Files affected:** `app/agents/orchestrator.py`, `app/core/llm.py`

### Phase 6B — MCP Integration
**Goal:** Expose agent tools as Model Context Protocol servers for external LLM clients.

- Wrap `get_team_by_code`, `predict_match`, `run_simulation` as MCP tools
- Stats Agent tools as MCP resources (team stats, H2H)
- Enables Claude Desktop / any MCP-compatible client to call the platform directly
- **Files affected:** New `app/mcp/` package; no existing code needs to change
- **Value:** High portfolio value; MCP is the emerging standard for agent tool integration

---

## What NOT to Build Yet

| Item | Reason to defer |
|------|----------------|
| RAGAS automated evaluation | Needs ground-truth dataset; corpus too small to measure meaningfully |
| Streaming agent graph (native LangGraph SSE) | Added complexity; current manual streaming path is correct and tested |
| WebSocket upgrade from SSE | SSE is sufficient for one-directional streaming; WebSocket adds bidirectional complexity without benefit |
| Multi-model routing (Haiku/Sonnet/Opus) | Current single-model path works; add when cost optimization is needed |
| Kubernetes / Helm | Docker Compose is sufficient until traffic justifies orchestration |

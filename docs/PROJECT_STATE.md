# Project State — FIFA 2026 Intelligence Platform

**Branch:** `phase-3b` (current working branch)  
**Stable tag:** `phase-3b-stable`  
**Last phase completed:** Phase 4A-Lite  
**Date:** 2026-06-11

---

## What Is This

A multi-agent AI backend for FIFA 2026 World Cup analytics. It exposes a FastAPI REST API that routes football questions through a LangGraph pipeline of specialist agents (stats, prediction, simulation, research, analyst) and returns structured responses with full agent traces. Supports both synchronous and SSE streaming chat.

---

## Implementation Status

### Core Infrastructure
| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI app | ✅ Complete | `app/main.py`, versioned at `/api/v1` |
| PostgreSQL (async) | ✅ Complete | SQLAlchemy 2.x async engine, `asyncpg` driver |
| Alembic migrations | ✅ Complete | 2 migrations: initial schema + prediction/simulation tables |
| SQLite fallback (CI) | ✅ Complete | Detected via URL prefix; pool kwargs skipped for SQLite |
| Redis | ⚠️ Configured only | Client in `health.py`, URL in config; not used by any agent |
| ChromaDB | ✅ Functional | Synchronous `HttpClient`; 3 collections indexed |
| Docker Compose | ✅ Complete | Postgres 16, Redis 7, ChromaDB, API service with healthchecks |
| Prometheus metrics | ✅ Complete | `prometheus-fastapi-instrumentator` at `/metrics` |

### API Endpoints
| Endpoint | Method | Status | Persistence |
|----------|--------|--------|-------------|
| `/api/v1/health` | GET | ✅ | — |
| `/api/v1/teams` | GET/POST/PUT/DELETE | ✅ | PostgreSQL |
| `/api/v1/matches` | GET/POST | ✅ | PostgreSQL |
| `/api/v1/predictions` | POST/GET | ✅ | PostgreSQL (`predictions` table) |
| `/api/v1/simulation` | POST/GET | ✅ | PostgreSQL (`simulation_runs` table) |
| `/api/v1/chat` | POST | ✅ | PostgreSQL (`chat_sessions`, `chat_messages`) |
| `/api/v1/chat/stream` | POST | ✅ | PostgreSQL (via SSE generator) |
| `/api/v1/chat/{uuid}` | GET | ✅ | — |
| `/api/v1/chat/{uuid}` | DELETE | ✅ | — |

### Agent Pipeline
| Agent | Status | Blocking I/O |
|-------|--------|-------------|
| Orchestrator (intent + team extraction) | ✅ | None (pure regex) |
| Stats Agent (PostgreSQL lookup) | ✅ | Async (`AsyncSession`) |
| Prediction Agent (ELO-Poisson) | ✅ | None (pure Python) |
| Simulation Agent (Monte Carlo) | ✅ | `asyncio.to_thread` (Phase 4A-Lite fix) |
| Research Agent (ChromaDB RAG) | ✅ | Sync ChromaDB client (known debt) |
| Analyst Agent (LLM synthesis) | ✅ | Async OpenAI or local fallback |

### Streaming Chat
| Feature | Status |
|---------|--------|
| SSE streaming endpoint (`/chat/stream`) | ✅ |
| Non-streaming path parity | ✅ (Phase 4A-Lite fix) |
| `simulation_node` in streaming path | ✅ (Phase 4A-Lite fix) |
| Monte Carlo off event loop | ✅ (Phase 4A-Lite fix) |
| Persistence during stream (flush mid-generator) | ✅ |

### RAG Pipeline
| Collection | Documents | Status |
|------------|-----------|--------|
| `world_cup_history` | JSON corpus | ✅ Indexed |
| `team_profiles` | 48 team docs | ✅ Indexed |
| `match_reports` | Tactical reports | ✅ Indexed |
| Metadata filtering | — | ❌ Not implemented |
| Async ChromaDB client | — | ❌ Sync client blocks event loop |

### Auth / Security
| Feature | Status |
|---------|--------|
| JWT utilities (`security.py`) | ✅ Written |
| Auth middleware / route guards | ❌ Not wired |
| User model | ❌ Not implemented |
| `user_id` on `ChatSession` | ⚠️ Column exists, always `None` |

---

## Test Suite

**109 tests, 109 passing.** All run against SQLite in-memory (CI) and locally.

| Test Module | Tests | Coverage Area |
|-------------|-------|---------------|
| `test_orchestrator.py` | 16 | Intent classification, team extraction, graph routing |
| `test_prediction_agent.py` | 3 | ELO-Poisson model, XAI narrative |
| `test_research_agent.py` | 24 | RAG retrieval, query building, deduplication, interleaving |
| `test_simulation_agent.py` | 3 | Monte Carlo node, empty-team fallback, `asyncio.to_thread` |
| `test_stats_agent.py` | 3 | DB query helpers |
| `test_chat.py` | 13 | Session CRUD, streaming SSE, simulation_node routing |
| `test_health.py` | 2 | Health endpoint |
| `test_matches.py` | 8 | Match CRUD |
| `test_predictions.py` | 8 | Prediction persistence |
| `test_simulations.py` | 6 | Simulation persistence |
| `test_teams.py` | 12 | Team CRUD |
| `test_ingestion.py` | 11 | RAG ingestion pipeline |

---

## CI/CD

**GitHub Actions** (`.github/workflows/ci.yml`):
- Triggers on push to `main` and `phase-3b`; PRs to `main`
- Steps: `ruff check` → `mypy` (advisory, `continue-on-error: true`) → `pytest` → Codecov upload
- Second job: Docker image build (does not push)
- Database: `sqlite+aiosqlite:///:memory:` (no external services in CI)
- mypy is advisory (`continue-on-error: true`) — no hard gate yet

**Local toolchain:** `ruff` + `mypy --ignore-missing-imports --no-strict-optional` + `pytest`

---

## Known Issues / Technical Debt

1. **ChromaDB sync client** — `chromadb.HttpClient` is synchronous. Called from `research_node` (async) without `asyncio.to_thread`. Under load this blocks the event loop. Fix: wrap in `asyncio.to_thread` or switch to `AsyncHttpClient` when ChromaDB supports it stably.
2. **Redis unused** — Redis is in `requirements.txt`, configured in `settings`, health-checked, but no agent or API uses it. Intended for LangGraph checkpointing (Phase 4B).
3. **Auth not enforced** — `security.py` has JWT helpers; no route is guarded. `user_id` column on `ChatSession` is always `None`.
4. **mypy advisory** — `continue-on-error: true` on the mypy CI step. Several `type: ignore` comments in `chat.py` due to TypedDict merge patterns.
5. **No metadata filtering in RAG** — ChromaDB collections store metadata (`year`, `team_code`, etc.) but queries never filter by it. All retrieval is semantic-only.
6. **LLM local fallback** — When `OPENAI_API_KEY` is unset, `llm.py` returns deterministic template responses. All tests pass without an API key, but production requires a key.
7. **Stats Agent opens its own session** — `stats_node` opens `AsyncSessionLocal()` directly rather than receiving a `db` dependency. Bypasses the request-scoped session; fine for agent use but diverges from FastAPI DI pattern.

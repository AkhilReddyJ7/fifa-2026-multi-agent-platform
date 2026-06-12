# Architecture — FIFA 2026 Intelligence Platform

## System Overview

```
Client (HTTP/SSE)
      │
      ▼
  FastAPI (uvicorn)
  ├── /api/v1/teams        → PostgreSQL CRUD
  ├── /api/v1/matches      → PostgreSQL CRUD
  ├── /api/v1/predictions  → Agent pipeline → PostgreSQL persist
  ├── /api/v1/simulation   → Agent pipeline → PostgreSQL persist
  ├── /api/v1/chat         → Agent pipeline → PostgreSQL persist
  └── /api/v1/chat/stream  → Agent pipeline → SSE stream → PostgreSQL persist
          │
          ▼
  LangGraph StateGraph (PlatformState)
  ├── orchestrator_node  (regex intent + team code extraction)
  ├── stats_node         (PostgreSQL → team data, H2H, match stats)
  ├── prediction_node    (ELO-Poisson model — pure Python)
  ├── simulation_node    (Monte Carlo — asyncio.to_thread)
  ├── research_node      (ChromaDB RAG — 3 collections)
  └── analyst_node       (OpenAI GPT-4o or local fallback)
          │
    ┌─────┴──────────────────────┐
    ▼                            ▼
PostgreSQL (asyncpg)        ChromaDB (HTTP)
- teams, players            - world_cup_history
- matches, team_stats       - team_profiles
- predictions               - match_reports
- simulation_runs
- chat_sessions
- chat_messages

Redis (configured, unused in production paths)
```

---

## LangGraph Pipeline

**Graph type:** `StateGraph` with `PlatformState` TypedDict  
**Entry:** `START → orchestrator → stats → [conditional routing] → research → analyst → END`

### Routing Logic

```
stats_node output
    │
    ├── intent == "predict" AND len(team_codes) >= 2  →  prediction_node
    ├── intent == "simulate"                           →  simulation_node
    └── (all other intents)                            →  research_node
    
prediction_node  ──→  research_node
simulation_node  ──→  research_node
research_node    ──→  analyst_node  ──→  END
```

### Intent Classification (regex, `orchestrator.py`)

| Intent | Trigger keywords |
|--------|-----------------|
| `predict` | predict, vs, versus, who wins, chance, probability, odds, beat |
| `simulate` | simulat, tournament, bracket, champion, world cup winner, title |
| `analyze` | analyz, analys, profile, strength, weakness, tactic, form, squad |
| `lookup` | stats, statistics, record, history, h2h, head-to-head, played |
| `chat` | (default — no keyword match) |

### PlatformState Schema

```python
class PlatformState(TypedDict):
    query: str
    intent: str                         # predict | simulate | analyze | lookup | chat
    team_codes: List[str]               # FIFA 3-letter codes e.g. ["BRA", "ARG"]
    history: List[Dict[str, str]]       # prior chat turns

    team_data: Dict[str, Any]           # Stats Agent output
    prediction: Dict[str, Any]          # Prediction Agent output
    sim_results: Dict[str, Any]         # Simulation Agent output
    rag_docs: List[str]                 # Research Agent output (up to 6 chunks)

    response: str                       # Analyst Agent final text
    error: Optional[str]

    trace: Annotated[List[AgentTrace], operator.add]  # accumulates across all nodes
```

---

## Agent Details

### Orchestrator (`app/agents/orchestrator.py`)
- Pure regex classification; no LLM call
- Extracts team codes against a hard-coded set of all 48 FIFA 2026 qualifiers
- Both the LangGraph non-streaming path (`run_query`) and the streaming path (`event_generator`) use this node first

### Stats Agent (`app/agents/stats_agent.py`)
- Opens its own `AsyncSessionLocal` session (not request-scoped)
- Fetches: individual team profiles, top-11 players by rating, last-10 match stats, H2H for exactly two teams
- Always fetches `_all_teams` (ELO-ranked) when intent is `simulate` or `analyze`

### Prediction Agent (`app/agents/prediction_agent.py`)
- **Model:** ELO rating system (K=32, 400-point scale) + Dixon-Coles-inspired Poisson expected goals
- Requires exactly two `team_codes`; falls back gracefully otherwise
- All World Cup matches treated as neutral venue (no home advantage)
- Outputs: `home_win_prob`, `draw_prob`, `away_win_prob`, `expected_goals`, `confidence`, `feature_importances`, `explainability` (text narrative)
- No external libraries — pure `math` module

### Simulation Agent (`app/agents/simulation_agent.py`)
- **Model:** Monte Carlo — N independent tournament simulations (default 1,000, max 10,000)
- Full FIFA 2026 format: 12 groups of 4, top-2 + 8 best 3rd → Round of 32, single-elimination knockout
- CPU-bound loop wrapped with `asyncio.to_thread` (Phase 4A-Lite fix)
- Outputs: `win_probabilities`, `final_probabilities`, `semifinal_probabilities`, `expected_bracket`, `top_5_favorites`

### Research Agent (`app/agents/research_agent.py`)
- Queries all three ChromaDB collections with intent-aware, collection-specific queries
- Per-collection fetch sizes vary by intent (e.g., predict → more match reports; simulate → more history)
- MD5-based deduplication across collections
- Round-robin interleaving of results so analyst context is balanced across collections
- Analyst receives up to 6 document chunks

### Analyst Agent (`app/agents/analyst_agent.py`)
- LLM: OpenAI GPT-4o (`gpt-4o`) via async client
- Falls back to deterministic template responses when `OPENAI_API_KEY` is unset
- Builds structured context JSON from all agent outputs (truncates `_all_teams` to top-10 ELO)
- Two modes: `analyst_node` (single completion) and `analyst_stream` (SSE chunks via `chat_stream`)
- Temperature: 0.4

---

## Streaming Chat (SSE)

**Endpoint:** `POST /api/v1/chat/stream`  
**Response:** `StreamingResponse` with `media_type="text/event-stream"`

### SSE Protocol

```
data: [START]

data: <text chunk>

data: <text chunk>

...

data: {"event":"session","session_uuid":"<uuid>"}

data: [DONE]
```

### Streaming Execution Flow

The `event_generator` async generator inside `chat_stream_endpoint` manually chains the same nodes as the LangGraph graph (minus the graph compile overhead), reflecting the same routing logic as `_route_after_stats`:

```python
orchestrator_node → stats_node
    → if predict+2 teams: prediction_node
    → elif simulate:       simulation_node
    → research_node → analyst_stream (SSE chunks)
```

User message is flushed to DB before streaming starts. Assistant message (full concatenated response) is flushed after the last content chunk, before the session event.

---

## Database

**Engine:** PostgreSQL 16 (production), SQLite in-memory (CI/testing)  
**Driver:** `asyncpg` (async), `psycopg2-binary` (Alembic sync)  
**ORM:** SQLAlchemy 2.x with `mapped_column` / `Mapped[]` type annotations

### Schema Summary

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `teams` | `id`, `fifa_code` (unique), `elo_rating`, `form_index`, `confederation`, `group_label` | 48 FIFA 2026 qualifiers |
| `players` | `team_id` (FK), `position`, `caps`, `goals`, `rating`, `is_captain` | Cascade delete |
| `matches` | `home_team_id`, `away_team_id`, `tournament_year`, `stage`, `home_goals`, `away_goals` | Unique constraint on home+away+date+year |
| `team_stats` | `team_id`, `match_id`, `xg`, `possession`, `shots_on_target` | Per-match stats, JSON `extra_data` |
| `predictions` | `home_team_code`, `away_team_code`, `home_win_prob`, `draw_prob`, `away_win_prob`, `shap_values` (JSON) | Optional `match_id` FK |
| `simulation_runs` | `run_uuid`, `n_simulations`, `win_probabilities` (JSON), `bracket` (JSON) | One row per run |
| `chat_sessions` | `session_uuid`, `user_id` (always NULL) | UUID-addressable sessions |
| `chat_messages` | `session_id` (FK), `role`, `content`, `agent_trace` (JSON) | Cascade delete with session |

### Migrations

| ID | Description |
|----|-------------|
| `0001_initial_schema` | All core tables: teams, players, matches, team_stats |
| `0002_prediction_simulation_persistence` | `predictions` and `simulation_runs` tables |

Chat tables (`chat_sessions`, `chat_messages`) were added in Phase 3C but have no dedicated migration — they are created by `Base.metadata.create_all` in the test `conftest.py` and expected to be created via Alembic in production.

---

## RAG Pipeline

### ChromaDB Collections

| Collection | Content | Metadata |
|------------|---------|----------|
| `world_cup_history` | Tournament narratives, match summaries | `year`, `stage`, `home_code`, `away_code` |
| `team_profiles` | Squad identity, style, and tactical docs (one per team) | `team_code`, `team_name`, `confederation` |
| `match_reports` | Post-match tactical analysis reports | `year`, `stage`, `home_code`, `away_code` |

### Embedding
- ChromaDB default embedding model (sentence-transformers `all-MiniLM-L6-v2`)
- Distance metric: cosine (configured via `hnsw:space` collection metadata)

### Ingestion
- Synchronous (`app/rag/ingestion.py`) — for seed scripts only
- Data files: `app/rag/data/wc_history.json`, `team_profiles.json`, `match_reports.json`

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| API framework | FastAPI | 0.111.1 |
| ASGI server | Uvicorn | 0.30.1 |
| Async ORM | SQLAlchemy | 2.0.31 |
| Migrations | Alembic | 1.13.2 |
| Async DB driver | asyncpg | 0.29.0 |
| Data validation | Pydantic v2 | 2.8.2 |
| Agent orchestration | LangGraph | 0.2.28 |
| LLM client | OpenAI Python SDK | 1.40.0 |
| Vector DB | ChromaDB | 0.5.3 |
| Structured logging | structlog | 24.2.0 |
| Metrics | prometheus-fastapi-instrumentator | 7.0.0 |
| Auth utilities | python-jose, passlib | 3.3.0, 1.7.4 |
| HTTP client (tests) | httpx | 0.27.0 |
| Test runner | pytest + pytest-asyncio | 8.3.1 + 0.23.8 |

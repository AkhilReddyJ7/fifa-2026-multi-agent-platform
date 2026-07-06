# FIFA 2026 Multi-Agent Intelligence Platform

An AI-powered platform for FIFA 2026 World Cup analytics, match predictions, tournament simulation, and conversational AI analysis.

## Architecture Overview

```
React SPA  ←→  FastAPI Gateway  ←→  LangGraph Agent Core  ←→  PostgreSQL + ChromaDB + Redis
```

Five specialist agents (Stats, Prediction, Simulation, Research, Analyst) are orchestrated by a LangGraph StateGraph to answer complex football intelligence queries.

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, Zustand |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.x, Alembic |
| Agents | LangGraph, OpenAI-compatible LLM interface |
| Databases | PostgreSQL 16, ChromaDB, Redis 7 |
| Infra | Docker, GitHub Actions, Nginx, Prometheus |

> **No API key? No problem.** If `OPENAI_API_KEY` is unset, the LLM layer falls
> back to a deterministic local mode that formats agent outputs directly — the
> whole platform (predictions, simulation, chat) works offline. Set a key to get
> real LLM-written analysis.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12 (for local dev without Docker)

### 1. Clone and configure

```bash
git clone <repo>
cd fifa2026-platform
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY and OPENAI_API_KEY
```

### 2. Start all services

```bash
cd infra
docker compose up -d --build
```

This starts: PostgreSQL, Redis, ChromaDB, the FastAPI backend, and the React frontend.

### 3. Run migrations

```bash
docker compose exec api alembic upgrade head
```

### 4. Seed historical data

```bash
docker compose exec api python -m scripts.seed_data
```

### 5. Open the app

- **Frontend**: http://localhost:3000 — dashboard, prediction UI, tournament simulation, streaming analyst chat
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/api/v1/health

---

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Copy and edit env
cp ../.env.example .env

# Run migrations (PostgreSQL must be running)
alembic upgrade head

# Start dev server with auto-reload
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173, proxies /api to localhost:8000
```

---

## Running Tests

Tests use an **in-memory SQLite** database — no external services required.

```bash
cd backend
pip install aiosqlite
pytest tests/ -v
```

With coverage:

```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

---

## API Reference

### Teams

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/teams` | List all teams (pagination, filter by confederation/group) |
| POST | `/api/v1/teams` | Create a team |
| GET | `/api/v1/teams/{code}` | Get team by FIFA code (e.g. `BRA`) |
| PATCH | `/api/v1/teams/{code}` | Update team fields |
| DELETE | `/api/v1/teams/{code}` | Delete a team |
| GET | `/api/v1/teams/{code}/players` | List players |
| POST | `/api/v1/teams/{code}/players` | Add a player |

### Matches

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/matches` | List matches (filter by year, stage, team) |
| POST | `/api/v1/matches` | Create a match record |
| GET | `/api/v1/matches/{id}` | Get match detail with team names |
| GET | `/api/v1/matches/{id}/stats` | Per-team stats for a match |

### Predictions & Simulation

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/predictions` | Predict a match (`{home_team, away_team, stage}`) — probabilities, xG, XAI, analyst summary |
| POST | `/api/v1/simulation` | Monte Carlo tournament simulation (`{n_simulations, seed}`) — champion/final/semifinal odds |

### Chat

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/chat` | Ask the analyst — full agent pipeline, complete response |
| POST | `/api/v1/chat/stream` | Same, streamed as Server-Sent Events |

### System

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Service health (DB, Redis, ChromaDB) |
| GET | `/metrics` | Prometheus metrics scrape endpoint |

---

## Project Structure

```
fifa2026-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/         # Route handlers (teams, matches, predictions, simulation, chat)
│   │   ├── agents/         # LangGraph orchestrator + 5 specialist agents
│   │   ├── core/           # Config, security, LLM client (with offline fallback)
│   │   ├── db/             # SQLAlchemy models, migrations
│   │   ├── rag/            # ChromaDB client, ingestion, seed corpora
│   │   ├── ml/             # ELO-Poisson predictor, Monte Carlo simulator
│   │   └── main.py
│   ├── scripts/
│   │   └── seed_data.py    # Historical WC data loader
│   ├── tests/
│   ├── Dockerfile
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # Dashboard, Predict, Simulate, Chat views
│   │   ├── lib/api.ts      # Typed API client + SSE stream reader
│   │   └── store.ts        # Zustand chat store
│   ├── Dockerfile          # Node build → nginx static + /api proxy
│   └── nginx.conf
├── infra/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── nginx/
└── .github/workflows/ci.yml
```

---

## Roadmap

| Phase | Focus | Status |
|---|---|---|
| **1** | Foundation: FastAPI, DB, Docker, seed data | ✅ Complete |
| **2** | Agent Core: LangGraph orchestrator + 5 agents | ✅ Complete |
| **3** | Simulation + RAG: Monte Carlo, ChromaDB retrieval | ✅ Complete |
| **4** | Chat + Streaming: SSE streaming, Analyst Agent | ✅ Complete |
| **5** | Frontend: React dashboard, prediction UI, streaming chat | ✅ Complete |
| **6** | Production: nginx edge, Docker images for both tiers, CI for backend + frontend | ✅ Complete |

---

## Contributing

1. Fork the repo and create a feature branch
2. Run `pytest` locally — all tests must pass
3. Open a PR against `develop`

## License

MIT

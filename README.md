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
| Frontend | React 18, TypeScript, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.x, Alembic |
| Agents | LangGraph, OpenAI-compatible LLM interface |
| Databases | PostgreSQL 16, ChromaDB, Redis 7 |
| Infra | Docker, GitHub Actions, Nginx, Prometheus |

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
docker compose up -d
```

This starts: PostgreSQL, Redis, ChromaDB, and the FastAPI backend.

### 3. Run migrations

```bash
docker compose exec api alembic upgrade head
```

### 4. Seed historical data

```bash
docker compose exec api python -m scripts.seed_data
```

### 5. Open the API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/api/v1/health

---

## Local Development (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install aiosqlite   # for SQLite test backend

# Copy and edit env
cp ../.env.example .env

# Run migrations (PostgreSQL must be running)
alembic upgrade head

# Start dev server with auto-reload
uvicorn app.main:app --reload --port 8000
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
│   │   ├── api/v1/         # Route handlers
│   │   ├── agents/         # LangGraph agents (Phase 2)
│   │   ├── core/           # Config, security
│   │   ├── db/             # SQLAlchemy models, migrations
│   │   ├── rag/            # ChromaDB client, ingestion
│   │   ├── ml/             # Prediction models (Phase 2)
│   │   └── main.py
│   ├── scripts/
│   │   └── seed_data.py    # Historical WC data loader
│   ├── tests/
│   ├── Dockerfile
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/               # Phase 5
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
| 2 | Agent Core: LangGraph orchestrator + 5 agents | Planned |
| 3 | Simulation + RAG: Monte Carlo, ChromaDB retrieval | Planned |
| 4 | Chat + Streaming: WebSocket, Analyst Agent | Planned |
| 5 | Frontend: React dashboard, prediction UI | Planned |
| 6 | Production: observability, load testing, security | Planned |

---

## Contributing

1. Fork the repo and create a feature branch
2. Run `pytest` locally — all tests must pass
3. Open a PR against `develop`

## License

MIT

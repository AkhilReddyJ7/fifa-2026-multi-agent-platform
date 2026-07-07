.PHONY: help up seed down logs restart test lint frontend-dev prod-up prod-down

help:            ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up:              ## Build and start the full dev stack (frontend :3000, API :8000)
	cd infra && docker compose up -d --build

seed:            ## Run DB migrations and load seed + RAG data (run once after `make up`)
	cd infra && docker compose exec api alembic upgrade head
	cd infra && docker compose exec api python -m scripts.seed_data

down:            ## Stop the stack (keeps data volumes)
	cd infra && docker compose down

logs:            ## Tail API logs
	cd infra && docker compose logs -f api

restart:         ## Rebuild and restart api + frontend after code changes
	cd infra && docker compose up -d --build api frontend

test:            ## Run the backend test suite (needs backend/.venv — see README)
	cd backend && .venv/bin/python -m pytest tests/ -q

lint:            ## Lint backend (ruff) and frontend (oxlint)
	cd backend && .venv/bin/ruff check app tests
	cd frontend && npm run lint

frontend-dev:    ## Vite dev server with hot reload (proxies /api to :8000)
	cd frontend && npm run dev

prod-up:         ## Start the production stack (TLS-ready edge nginx on :80/:443)
	cd infra && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

prod-down:       ## Stop the production stack
	cd infra && docker compose -f docker-compose.yml -f docker-compose.prod.yml down

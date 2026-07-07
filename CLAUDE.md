# FIFA 2026 Multi-Agent Prediction Platform

FastAPI backend + LangGraph 5-agent pipeline + Monte Carlo simulator + Chroma RAG, with a React 19 / Vite / Tailwind 4 frontend. Repo: AkhilReddyJ7/fifa-2026-multi-agent-platform. All six build phases are complete and verified end-to-end (July 2026).

## Run & test
- Full stack: `cd infra && docker compose up -d --build` → frontend on :3000, API on :8000.
- Backend venv: `backend/.venv` (created with `uv venv --python 3.12`).
- Tests: from `backend/`, `.venv/bin/python -m pytest tests/` — 82 tests, all should pass.
- The LLM layer has a deterministic no-API-key local mode: everything runs and tests pass **without** an OPENAI_API_KEY. Don't add code that assumes the key exists.
- Frontend screenshots: `frontend/scripts/screenshot.mjs` (headless Chromium). Needs `LD_LIBRARY_PATH` pointing at libs extracted via `apt-get download libnspr4 libnss3 libasound2t64` (no sudo).

## Gotchas (each cost real debugging time — don't re-learn them)
- **pydantic-settings JSON-decodes `List[str]` env vars.** Keep `allowed_origins` typed as `str` in Settings and split it manually; a `List[str]` field crashes on plain comma-separated env values.
- **LangGraph rejects node names that shadow state keys.** The prediction node is named `prediction_agent` for this reason — don't rename nodes to match state fields.
- **Chroma server image is pinned to 0.5.3** to match the Python client. Don't bump one without the other.
- **The backend Docker build needs `g++`** (for chroma-hnswlib). It's in the Dockerfile; don't remove it when slimming the image.

## Workflow
- `make help` lists dev targets (`up`, `seed`, `test`, `lint`, `frontend-dev`, `prod-up`).
- Verify UI changes with the screenshot suite before committing (see Run & test above).

# End-to-End Implementation Plan (AI-Executable)

This is a precise, step-by-step plan an AI (or engineer) can follow to implement the demo from scratch. Each step includes success criteria, validation checks, and fallback/rollback notes.

## Conventions
- Shell is at repo root unless specified.
- Do not commit secrets. Use `.env` and `.env.local`.
- Run checks after each phase; do not proceed if checks fail.

## Phase 0 — Bootstrap & Prereqs
1) Verify prerequisites installed
- Node 18+, Python 3.10+, Git
- Success: `node -v`, `python --version`, `git --version` exit 0

2) Create base folders if missing
- Create: `backend/`, `frontend/`
- Success: Folders exist and are writable

3) Create backend requirements file
- Write `backend/requirements.txt` per Setup Guide
- Success: File exists with required packages

Validation checks
- `python -m venv .venv` and `pip install -r backend/requirements.txt` completes
- If install fails, pin versions or clear cache (`pip cache purge`) and retry

## Phase 1 — Backend Scaffolding (FastAPI)
1) Create FastAPI app
- File: `backend/main.py` with CORS, `/health` endpoint and `/api/test-prompt`
- Success: `uvicorn backend.main:app --reload --port 8000` starts, `/health` returns 200

2) Settings management
- Add `backend/core/settings.py` using pydantic-settings (GEMINI_API_KEY, DATABASE_URL)
- Success: `from core.settings import settings` loads values from `.env`

3) Logging
- Add `structlog` setup `backend/core/logging.py` with JSON logs to stdout
- Success: Startup logs in JSON format include service name

Validation checks
- Hit `/docs` renders OpenAPI
- CORS allows `http://localhost:3000`

## Phase 2 — Data Models & DB (SQLAlchemy + Alembic)
1) Define SQLAlchemy models
- `backend/db/schemas.py`: `AgentModel`, `LinkModel`, `RunModel`
- Success: Models import without error

2) DB engine session
- `backend/db/database.py` with sessionmaker and engine from `DATABASE_URL`
- Success: Context manager yields session

3) Alembic init and migration
- Initialize Alembic in `backend/db/migrations`
- Autogenerate initial schema migration
- Success: `alembic upgrade head` creates tables

Validation checks
- Create and query an `AgentModel` row in an interactive shell without error
- Rollback: `alembic downgrade -1` if migration wrong

## Phase 3 — API Routes (Agents, Links, Runs)
1) Pydantic API models
- `backend/core/models.py` (AgentCreate/Update, Link, RunRequest, Run/RunLog)
- Success: Models validate per Data Models doc

2) Agents routes
- `backend/api/routes/agents.py` CRUD with DB integration
- Success: `POST /api/agents` creates; `GET /api/agents` lists; `PUT/DELETE` work

3) Links routes
- `backend/api/routes/links.py` create/delete link with cycle prevention
- Success: Prevent duplicate links; 409 on cycle attempt

4) Runs routes
- `backend/api/routes/runs.py` `POST /api/runs` (create run) and `GET /api/runs/{id}` (status)
- Success: Creates run row; returns pending/running status

Validation checks
- Add minimal `backend/api/router.py` and include in `main.py`
- Use `httpx` or curl to exercise endpoints; verify 2xx responses and DB writes

## Phase 4 — Orchestrator & SSE Streaming
1) Orchestrator skeleton
- `backend/core/orchestrator.py` with topological traversal and per-level parallel fan-out
- Success: Function signature `execute_run(run_id, root_agent_id, input_data, stream)` exists

2) SSE endpoint
- `GET /api/runs/{id}/stream` yields `event: status|log|output|error` lines
- Heartbeats every 20–30s; supports `Last-Event-ID`
- Success: Browser EventSource receives events without disconnects

3) Error handling
- Retries with exponential backoff (3 attempts) and circuit breaker for repeated failures
- Success: Errors surfaced as `event: error`, run status becomes `failed`

Validation checks
- Local manual run emits `status -> output -> completed`
- Kill/restart server: SSE reconnects and resumes

## Phase 5 — Gemini Integration
1) Gemini client wrapper
- `backend/core/gemini_client.py` with `generate_text` and `generate_streaming`
- Success: Returns text for dummy prompts with `GEMINI_API_KEY`

2) Wire orchestrator to Gemini
- Use agent.system_prompt + context; respect parameters (temperature, max_tokens)
- Success: Real responses stream via SSE

3) Tool: HTTP fetch
- `backend/utils/tools.py` `http_fetch(url)` using `httpx` with timeout, UA, domain allowlist
- Success: Researcher agent can fetch allowed pages; non-allowlisted blocked

Validation checks
- Rate limiting (slowapi) mounted for `/api/runs` (e.g., 5/min per IP)
- Safety limits: max tokens 1000; temperature per agent

## Phase 6 — Frontend Scaffold (Next.js + Tailwind)
1) Create Next.js app
- In `frontend/`, ensure Next.js + Tailwind installed per Setup Guide
- Success: `npm run dev` serves at 3000

2) Install libs
- `zustand`, `@tanstack/react-query`, `reactflow`
- Success: Deps installed and imported without TS errors

3) App structure
- Create `app/(lab)/page.tsx` with layout
- Success: Page renders; shows header shell

Validation checks
- ESLint/TypeScript pass (`npm run lint`, `tsc -p .`)

## Phase 7 — Canvas, Drawer, Console
1) Canvas
- `components/canvas/AgentCanvas.tsx` using React Flow controlled nodes/edges
- Success: Add node via plus button; render node with handles

2) Drawer
- `components/drawer/AgentDrawer.tsx` to edit name, role, system_prompt, parameters
- Success: Persist edits via `PUT /api/agents/{id}` (optimistic update)

3) Console
- `components/console/RunsConsole.tsx` to start run and stream via EventSource
- Success: Live logs/outputs appear during run

Validation checks
- Visual smoke test: create agents, link, edit, run end-to-end
- Undo/delete interactions behave predictably

## Phase 8 — API Integration & State
1) Query client
- `lib/api.ts`: CRUD for agents, links, runs; SSE helper
- Success: Network calls resolve, errors surfaced via toasts

2) State slices
- `lib/store.ts`: graphSlice, agentSlice, runSlice with Immer
- Success: No unnecessary re-renders; selectors used with shallow compare

3) Types
- `lib/types.ts`: Mirror backend models
- Success: TS types align with API responses

Validation checks
- React Query devtools show caches keyed by `['agents']`, `['runs', id]`
- Graph remains consistent on CRUD and linking

## Phase 9 — Prompts & Tooling
1) Seed templates
- Add templates for ProductManager, Researcher, Designer
- Success: Creating from template fills prompt and defaults

2) Enable HTTP fetch tool
- Attach to Researcher; pass parent output as query terms; sanitize URLs
- Success: Outputs include summarized findings with sources

Validation checks
- Block non-allowlisted domains; confirm messaging is clear

## Phase 10 — Testing, QA, and Polish
1) Backend tests
- Pytest for routes, orchestrator traversal, HTTP tool (mocked)
- Success: `pytest` all green

2) Frontend tests
- Basic component tests for canvas, drawer
- Success: `npm test` green

3) Lint & format
- Backend: `black .`, `ruff check .`
- Frontend: `npm run format`, `npm run lint`
- Success: No errors; CI-ready

4) Manual E2E script
- Script detailed in Demo Spec Run Flow; verify 5-step run completes
- Success: Transcript exported and readable

5) Observability
- Structured logs include run_id, agent_id
- SSE heartbeat validated; reconnection tested

## Phase 11 — Deployment (Optional)
1) Backend
- Containerize; deploy to Fly/Render/Cloud Run; set secrets; healthchecks
- Success: `/health` 200; `/docs` loads; CORS set to frontend domain

2) Frontend
- Deploy to Vercel; set `NEXT_PUBLIC_API_BASE_URL`
- Success: Demo works end-to-end in prod

## Redundant Checks (Every Phase)
- Healthcheck: `/health` 200 when backend touched
- Lint/format: run language-appropriate tools
- Minimal functional test of newly added feature
- Rollback: revert last change if validation fails

## Acceptance Criteria (Definition of Done)
- Can create agents via UI and API
- Can link parent → child visually and in DB
- Can edit prompts and parameters
- Run from root executes with SSE streaming and per-agent outputs
- HTTP fetch tool works within allowlist and shows results
- All tests green; lint clean; logs structured
- Docs updated: Demo Spec, API, System Architecture



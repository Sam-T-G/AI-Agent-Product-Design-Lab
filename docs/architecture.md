# Architecture Overview

The current build ships a single FastAPI backend plus a Next.js frontend. The two communicate via REST + Server-Sent Events (SSE); users supply their own Gemini API keys from the browser.

## High-level diagram
```
Browser (Next.js) ── REST/SSE ── FastAPI ── Gemini API
                               │
                               └── SQLite/PostgreSQL
```

## Backend (FastAPI)
- `backend/main.py` boots the app, sets CORS, and mounts the versioned API router.
- `backend/api/routes/` exposes CRUD for sessions, agents, links, and runs. Each endpoint requires a `session_id` query parameter to guarantee isolation.
- `backend/core/orchestrator_v2.py` is the run engine: it walks the agent hierarchy, calls Gemini with the supplied key, streams events back via SSE, and persists outputs/logs to `RunModel`.
- `backend/db/` contains the SQLAlchemy models and DB session helpers. SQLite is used locally (`agents.db`), but the `DATABASE_URL` env var can target Postgres for deployment.
- Gemini credentials are never stored server-side: every run uses the `X-Gemini-Api-Key` header forwarded from the browser or the `api_key` query parameter on the SSE stream.

## Frontend (Next.js 16 / React 19)
- `frontend/app/page.tsx` orchestrates the UI shell: session modal, API key modal, React Flow canvas, drawer, and chat.
- `frontend/lib/api.ts` wraps fetch calls. Each request reads `SESSION_ID` from `localStorage` and appends it to the query string; errors surface through the browser console.
- `frontend/components/canvas/AgentCanvas.tsx` renders and edits the agent graph via React Flow.
- `frontend/components/drawer/AgentDrawer.tsx` auto-saves agent edits after a short debounce.
- `frontend/components/chat/ChatInterface.tsx` starts runs, uploads optional images, and streams SSE events for real-time output.

## Data flow summary
1. User selects a session → `SESSION_ID` stored client-side.
2. Agents are created/updated via REST calls (`/api/agents`). Positions and parent links live in the database.
3. Chat interface posts to `/api/runs` with the root agent id, input payload, and optional base64 images. The request body is stored in `RunModel`.
4. Frontend opens `/api/runs/{run_id}/stream?session_id=...&api_key=...` as an `EventSource`. The backend orchestrator pushes logs/output chunks until completion.
5. Once complete, the UI shows the aggregated text and stores the conversation history locally.

This simplified footprint intentionally omits the previous collaboration stack, making the system easier to reason about and deploy.

# AI Agent Product Design Lab

A focused baseline for designing session-scoped AI agent hierarchies, editing their prompts/parameters, and running conversations through a Gemini-powered orchestrator. Real-time collaboration and other experimental features have been removed so this repo represents the canonical, working build.

## What you get
- **FastAPI backend** with session + agent CRUD, SSE streaming runs, Gemini integration, and SQLite storage by default
- **Next.js frontend** with a React Flow canvas, agent drawer editor, and chat interface that streams run output
- **Bring-your-own Gemini key** stored client-side (per browser) and forwarded with each run request

## Quick start
### Prerequisites
- Python 3.10+
- Node.js 18+
- A Gemini API key (https://makersuite.google.com/app/apikey)

### Backend setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r backend/requirements.txt
cat <<'ENV' > backend/.env
GEMINI_API_KEY=your_gemini_key
DATABASE_URL=sqlite:///./agents.db
ENV
```

### Frontend setup
```bash
cd frontend
npm install
cat <<'ENV' > .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
ENV
```

### Run everything
```bash
# Backend
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm run dev
```
Visit http://localhost:3000 and select/create a session. After selecting a session you’ll be prompted for your Gemini API key.

## Project layout
```
backend/   FastAPI app, SQLAlchemy models, orchestrator, requirements
frontend/  Next.js client, React Flow canvas, chat UI, Zustand stores
scripts/   Utility shell scripts (deployment/test helpers)
docs/      Fresh documentation starting point
```

## Development notes
- The backend expects a clean database schema when it boots (`Base.metadata.create_all`). Delete `backend/agents.db` if you need a reset.
- SSE runs forward the browser-provided Gemini key; no key is stored on the server. Frontend errors usually mean the key is missing/invalid.
- When editing agents, the drawer auto-saves after a short debounce. If an agent disappears (e.g., session reset) you’ll see a 404—select or create a new agent before editing again.

## Next steps
- Flesh out the new documentation set in `docs/`
- Add automated tests around agent CRUD + run orchestration
- Wire up deployment scripts for the new simplified architecture

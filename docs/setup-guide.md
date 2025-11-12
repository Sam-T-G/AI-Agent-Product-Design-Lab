# Setup Guide

This guide walks through bringing the AI Agent Product Design Lab up on a local workstation without Docker.

## 1. Prerequisites
- **Python 3.10+** (use `pyenv`, `conda`, or system Python)
- **Node.js 18+** (Node 20 works as well)
- **npm** (ships with Node)
- **A Gemini API key** (https://makersuite.google.com/app/apikey)

## 2. Clone and bootstrap
```bash
git clone <repo-url>
cd AI-Agent-Product-Design-Lab
```

### Python environment
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r backend/requirements.txt
cat <<'ENV' > backend/.env
GEMINI_API_KEY=replace_me
dATABASE_URL=sqlite:///./agents.db
ENV
```

### Node dependencies
```bash
cd frontend
npm install
cat <<'ENV' > .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
ENV
```

## 3. Run the stack
Open two terminals:

**backend**
```bash
cd AI-Agent-Product-Design-Lab/backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000
```

**frontend**
```bash
cd AI-Agent-Product-Design-Lab/frontend
npm run dev
```

Visit http://localhost:3000, create/select a session, and supply your Gemini key when prompted.

## 4. Resetting state
- Delete `backend/agents.db` to start with a clean database.
- Clear `localStorage` keys `SESSION_ID` and `GEMINI_API_KEY` from the browser if you need to reset the client.

## 5. Troubleshooting
| Symptom | Fix |
| --- | --- |
| `422 Unprocessable Content` when listing agents | Create/select a session so `session_id` is sent with each request. |
| `Gemini API key missing` warnings | Open the “Change API Key” button in the header and re-enter the key. |
| SSE stream errors | Ensure the backend log (`/tmp/backend.log`) shows `gemini_generate_start` events—invalid keys or network issues will surface there. |

That’s it—the app now runs entirely without Docker.

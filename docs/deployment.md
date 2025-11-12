# Deployment Notes

The project no longer relies on Docker images; instead, treat the frontend and backend as independent services. Below are pragmatic deployment options.

## Environment variables
Backend (`uvicorn main:app ...`):
```
GEMINI_API_KEY=<optional fallback key>
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/agent_lab
CORS_ORIGINS=["https://your-frontend-domain"]
LOG_LEVEL=INFO
```
Frontend (`next build && next start`):
```
NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain/api
NEXT_PUBLIC_BACKEND_ORIGIN=https://your-backend-domain  # optional, used for rewrites
```
Each browser still prompts for a Gemini key; setting `GEMINI_API_KEY` on the backend simply allows server-side testing tools to use a default.

## Minimal hosting recipe
### Backend (Fly.io / Render / VM)
1. Provision a Python 3.11 environment.
2. Copy `backend/` plus `requirements.txt`.
3. Install deps: `pip install -r backend/requirements.txt`.
4. Create a `.env` or configure platform secrets with the variables above.
5. Launch `uvicorn main:app --host 0.0.0.0 --port $PORT`.
6. Expose HTTPS via the platform’s load balancer.

### Frontend (Vercel / Netlify / Static host)
1. Build once: `cd frontend && npm install && npm run build`.
2. Serve with `next start` or export to static if you introduce APIs for dynamic pieces.
3. Set `NEXT_PUBLIC_API_BASE_URL` to the backend URL.
4. Ensure the backend’s CORS list includes the frontend origin.

## Logs & monitoring
- Backend logs stream to stdout and can be captured by the hosting provider. Key events are prefixed with `sse_`, `orchestrator_`, and `gemini_`.
- Frontend logs stay in the browser console; for production observability, integrate a client-side logger (e.g., Sentry) that redacts the Gemini key.

## Zero-downtime updates
1. Deploy backend changes first; they are backward compatible if the REST schema doesn’t change.
2. Deploy frontend once the backend is healthy. Users will keep their `SESSION_ID` and `GEMINI_API_KEY` in localStorage through the update.

## Future work
- Provide infra-as-code once the hosting target is finalized.
- Automate DB migrations with Alembic when we introduce schema changes beyond the current create-all approach.

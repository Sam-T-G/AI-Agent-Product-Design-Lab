# Deployment Guide (Docker + Google Cloud Run)

## Overview
This app is split into:
- Backend: FastAPI at `/backend`
- Frontend: Next.js at `/frontend`

Frontend talks to backend via `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000/api`).
Users provide their own Gemini API key via the in-app modal; it is stored in browser `localStorage` and sent in header `X-Gemini-Api-Key` to the backend.

## Local with Docker Compose

```bash
# from repo root
docker compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/health
```

To change the API URL the frontend uses:
- Edit `docker-compose.yml` arg `NEXT_PUBLIC_API_BASE_URL` under `frontend`.

## Cloud Run (recommended)

Build and push images:
```bash
# Backend
PROJECT_ID=YOUR_PROJECT
REGION=us-central1
BACKEND_IMAGE=gcr.io/$PROJECT_ID/agent-lab-backend:latest
FRONTEND_IMAGE=gcr.io/$PROJECT_ID/agent-lab-frontend:latest

gcloud builds submit --tag $BACKEND_IMAGE --project $PROJECT_ID --config <(cat <<'EOF'
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build','-t','$BACKEND_IMAGE','-f','backend/Dockerfile','.']
images: ['$BACKEND_IMAGE']
EOF
)

gcloud builds submit --tag $FRONTEND_IMAGE --project $PROJECT_ID --config <(cat <<'EOF'
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build','-t','$FRONTEND_IMAGE','-f','frontend/Dockerfile','--build-arg','NEXT_PUBLIC_API_BASE_URL=https://YOUR_BACKEND_HOST/api','.']
images: ['$FRONTEND_IMAGE']
EOF
)
```

Deploy backend:
```bash
BACKEND_SVC=agent-lab-backend

gcloud run deploy $BACKEND_SVC \
  --image=$BACKEND_IMAGE \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --set-env-vars=CORS_ORIGINS=["https://YOUR_FRONTEND_HOST"] \
  --min-instances=0 --max-instances=3

# Get the URL output by gcloud (e.g., https://backend-xyz.a.run.app)
```

Deploy frontend:
```bash
FRONTEND_SVC=agent-lab-frontend
BACKEND_URL=https://<backend-url-from-previous-step>

gcloud run deploy $FRONTEND_SVC \
  --image=$FRONTEND_IMAGE \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --port=3000

# Frontend will be at its Cloud Run URL (e.g., https://frontend-xyz.a.run.app)
```

Update CORS
- In backend, CORS is driven by `settings.cors_origins`. Set env in Cloud Run like:
  - `CORS_ORIGINS=["https://YOUR_FRONTEND_HOST"]` (JSON array)
  - or `CORS_ORIGINS=["*"]` for testing only

## Production notes
- API key injection modal works in production the same as dev; the key is stored in `localStorage` and added as `X-Gemini-Api-Key` for all requests.
- Ensure the backend accepts the header (it does: `allow_headers=["*"]`).
- SSE streaming is supported by Cloud Run; avoid proxies that buffer responses.
- For custom domains, update `CORS_ORIGINS` and rebuild/redeploy the frontend with `NEXT_PUBLIC_API_BASE_URL` set to the backend domain.

## Health checks
- Backend: `GET /health` should return `{ "status": "healthy" }`.
- Frontend: Next.js default 200 at `/`.

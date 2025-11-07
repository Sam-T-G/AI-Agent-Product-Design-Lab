#!/usr/bin/env bash
set -euo pipefail

# Config
PROJECT_ID="284476306767"   # Using provided project number
REGION="us-central1"
BACKEND_SVC="agent-lab-backend"
FRONTEND_SVC="agent-lab-frontend"
BACKEND_IMAGE="gcr.io/$PROJECT_ID/${BACKEND_SVC}:latest"
FRONTEND_IMAGE="gcr.io/$PROJECT_ID/${FRONTEND_SVC}:latest"

echo "Project: $PROJECT_ID | Region: $REGION"
gcloud config set project "$PROJECT_ID"
gcloud config set run/region "$REGION"

echo "Building backend image..."
gcloud builds submit \
  --tag "$BACKEND_IMAGE" \
  --config <(cat <<'EOF'
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build','-t','$BACKEND_IMAGE','-f','backend/Dockerfile','.']
images: ['$BACKEND_IMAGE']
EOF
)

echo "Deploying backend to Cloud Run..."
gcloud run deploy "$BACKEND_SVC" \
  --image="$BACKEND_IMAGE" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --min-instances=0 \
  --max-instances=3 \
  --set-env-vars=CORS_ORIGINS='["*"]'

BACKEND_URL="$(gcloud run services describe "$BACKEND_SVC" --format='value(status.url)')"
echo "Backend URL: $BACKEND_URL"

echo "Building frontend image with API base: ${BACKEND_URL}/api ..."
gcloud builds submit \
  --tag "$FRONTEND_IMAGE" \
  --config <(cat <<'EOF'
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build','-t','$FRONTEND_IMAGE','-f','frontend/Dockerfile','--build-arg','NEXT_PUBLIC_API_BASE_URL=__API_BASE__']
images: ['$FRONTEND_IMAGE']
EOF
) | sed "s|__API_BASE__|${BACKEND_URL}/api|"

echo "Deploying frontend to Cloud Run..."
gcloud run deploy "$FRONTEND_SVC" \
  --image="$FRONTEND_IMAGE" \
  --platform=managed \
  --allow-unauthenticated \
  --port=3000

FRONTEND_URL="$(gcloud run services describe "$FRONTEND_SVC" --format='value(status.url)')"
echo "Frontend URL: $FRONTEND_URL"

echo "Locking backend CORS to frontend origin..."
gcloud run services update "$BACKEND_SVC" \
  --set-env-vars=CORS_ORIGINS="[\"${FRONTEND_URL}\"]"

echo "Done."
echo "Visit: ${FRONTEND_URL}"
echo "Backend health: curl ${BACKEND_URL}/health"



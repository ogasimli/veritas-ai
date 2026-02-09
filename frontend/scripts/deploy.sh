#!/bin/bash
set -e

# Configuration
REGION="us-central1"
PROJECT_ID=$(gcloud config get-value project)
SUFFIX="${DEPLOY_ENV:+-$DEPLOY_ENV}"
SERVICE_NAME="veritas-ai-frontend${SUFFIX}"
REPO_NAME="veritas-ai-repo"

# Get Backend URL (required for build)
BACKEND_SERVICE_NAME="veritas-ai-backend${SUFFIX}"
BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE_NAME" --region="$REGION" --format='value(status.url)')

if [ -z "$BACKEND_URL" ]; then
    echo "❌ Error: Backend service not found. Deploy backend first."
    exit 1
fi

echo "🚀 Starting Frontend Deployment for Project: $PROJECT_ID in $REGION"
echo "📡 Backend API URL: $BACKEND_URL"

# ==============================================================================
# 1. Enable APIs
# ==============================================================================
echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com

# ==============================================================================
# 2. Build & Deploy to Cloud Run
# ==============================================================================
echo "Building and Deploying Frontend to Cloud Run..."

# Ensure Artifact Registry repo exists (reuse backend repo)
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" >/dev/null 2>&1; then
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Docker repository for Veritas AI"
fi

IMAGE_URL="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME"

# Navigate to frontend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$FRONTEND_DIR"

# Build with backend URL as build arg
echo "Submitting build to Cloud Build..."
gcloud builds submit \
    --config=cloudbuild.yaml \
    --substitutions=_IMAGE_URL="$IMAGE_URL",_BACKEND_URL="$BACKEND_URL" \
    .

echo "Deploying Container..."
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_URL" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --timeout=3600

FRONTEND_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)')
echo "✅ Frontend Deployment Complete!"
echo "Service URL: $FRONTEND_URL"

# Update backend CORS to allow this frontend origin.
# Cloud Run exposes services on multiple URL formats, so we read them all from
# the run.googleapis.com/urls annotation to avoid CORS mismatches.
ALLOWED_ORIGINS=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" \
    --format='value(metadata.annotations."run.googleapis.com/urls")' \
    | python3 -c "import sys,json; print(','.join(json.load(sys.stdin)))" 2>/dev/null \
    || true)
if [ -z "$ALLOWED_ORIGINS" ]; then
    ALLOWED_ORIGINS="*"
    echo "⚠️  Could not read service URLs from Cloud Run annotations."
    echo "  ALLOWED_ORIGINS defaulting to '*'. Update manually if needed."
fi

echo "Updating backend ALLOWED_ORIGINS to $ALLOWED_ORIGINS..."
gcloud run services update "$BACKEND_SERVICE_NAME" \
    --region "$REGION" \
    --update-env-vars "^||^ALLOWED_ORIGINS=${ALLOWED_ORIGINS}"
echo "✅ Backend ALLOWED_ORIGINS updated."

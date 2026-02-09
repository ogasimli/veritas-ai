#!/bin/bash
set -e

REGION="us-central1"
SUFFIX="${DEPLOY_ENV:+-$DEPLOY_ENV}"
SERVICE_NAME="veritas-ai-frontend${SUFFIX}"

echo "Deleting $SERVICE_NAME..."
gcloud run services delete "$SERVICE_NAME" \
    --region "$REGION" \
    --quiet

echo "✅ $SERVICE_NAME deleted."

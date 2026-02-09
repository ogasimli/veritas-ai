#!/bin/bash
set -e

# Promote staging images to production.
#
# This deploys the exact images currently running on staging Cloud Run services
# to the production services, without rebuilding. Env vars, secrets, and Cloud
# SQL connections on the prod services are left untouched — only the container
# image is swapped.
#
# Prerequisites: both staging services and both prod services must already exist
# (i.e. you have run `make deploy` and `make deploy env=staging` at least once).
#
# Usage:
#   ./scripts/promote.sh                   # promote both backend and frontend
#   ./scripts/promote.sh --backend-only    # promote backend only
#   ./scripts/promote.sh --frontend-only   # promote frontend only

REGION="us-central1"
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

PROMOTE_BACKEND=true
PROMOTE_FRONTEND=true

for arg in "$@"; do
    case $arg in
        --backend-only)  PROMOTE_FRONTEND=false ;;
        --frontend-only) PROMOTE_BACKEND=false ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

echo "🚀 Promoting staging → production for project: $PROJECT_ID"
echo ""

# ---------------------------------------------------------------------------
# Read staging images
# ---------------------------------------------------------------------------
get_image() {
    local service=$1
    gcloud run services describe "$service" \
        --region="$REGION" \
        --format='value(spec.template.spec.containers[0].image)' 2>/dev/null
}

if [ "$PROMOTE_BACKEND" = true ]; then
    BACKEND_IMAGE=$(get_image "veritas-ai-backend-staging")
    if [ -z "$BACKEND_IMAGE" ]; then
        echo "❌ Error: Could not read veritas-ai-backend-staging image. Is it deployed?"
        exit 1
    fi
    echo "  Backend staging image:  $BACKEND_IMAGE"
fi

if [ "$PROMOTE_FRONTEND" = true ]; then
    FRONTEND_IMAGE=$(get_image "veritas-ai-frontend-staging")
    if [ -z "$FRONTEND_IMAGE" ]; then
        echo "❌ Error: Could not read veritas-ai-frontend-staging image. Is it deployed?"
        exit 1
    fi
    echo "  Frontend staging image: $FRONTEND_IMAGE"
fi

# ---------------------------------------------------------------------------
# Promote backend
# ---------------------------------------------------------------------------
if [ "$PROMOTE_BACKEND" = true ]; then
    echo ""
    echo "Promoting backend..."
    gcloud run services update "veritas-ai-backend" \
        --region="$REGION" \
        --image="$BACKEND_IMAGE"
    gcloud run services update-traffic "veritas-ai-backend" \
        --region="$REGION" \
        --to-latest
fi

# ---------------------------------------------------------------------------
# Promote frontend
# ---------------------------------------------------------------------------
if [ "$PROMOTE_FRONTEND" = true ]; then
    # Point the frontend at the prod backend URL (entrypoint.sh replaces the
    # placeholder at container startup).
    PROD_BACKEND_URL=$(gcloud run services describe "veritas-ai-backend" \
        --region="$REGION" \
        --format='value(status.url)')

    if [ -z "$PROD_BACKEND_URL" ]; then
        echo "❌ Error: Could not read production backend URL. Is veritas-ai-backend deployed?"
        exit 1
    fi

    echo ""
    echo "Promoting frontend (API URL → $PROD_BACKEND_URL)..."
    gcloud run services update "veritas-ai-frontend" \
        --region="$REGION" \
        --image="$FRONTEND_IMAGE" \
        --update-env-vars "NEXT_PUBLIC_API_URL=${PROD_BACKEND_URL}"
    gcloud run services update-traffic "veritas-ai-frontend" \
        --region="$REGION" \
        --to-latest
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "✅ Promotion complete!"
if [ "$PROMOTE_BACKEND" = true ]; then
    echo "  Backend:  $(gcloud run services describe veritas-ai-backend --region="$REGION" --format='value(status.url)')"
fi
if [ "$PROMOTE_FRONTEND" = true ]; then
    echo "  Frontend: $(gcloud run services describe veritas-ai-frontend --region="$REGION" --format='value(status.url)')"
fi

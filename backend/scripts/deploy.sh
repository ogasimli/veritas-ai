#!/bin/bash
set -e

# Configuration
REGION="us-central1"
PROJECT_ID=$(gcloud config get-value project)
SUFFIX="${DEPLOY_ENV:+-$DEPLOY_ENV}"
SERVICE_NAME="veritas-ai-backend${SUFFIX}"
DB_INSTANCE_NAME="veritas-ai-db-primary"
DB_NAME="veritas"
DB_USER="veritas_app"
BUCKET_NAME="${PROJECT_ID}-docs-${REGION}"
REPO_NAME="veritas-ai-repo"

# Resolve directories relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting Deployment for Project: $PROJECT_ID in $REGION"

# ==============================================================================
# 1. Enable APIs
# ==============================================================================
echo "Enable required APIs..."
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    storage.googleapis.com

# ==============================================================================
# 2. Cloud Storage (GCS)
# ==============================================================================
echo "checking GCS Bucket..."
if ! gsutil ls -b "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
    echo "Creating bucket gs://${BUCKET_NAME}..."
    gcloud storage buckets create "gs://${BUCKET_NAME}" --location="$REGION" --uniform-bucket-level-access
else
    echo "Bucket gs://${BUCKET_NAME} already exists."
fi

# ==============================================================================
# 3. Cloud SQL (PostgreSQL)
# ==============================================================================
echo "checking Cloud SQL Instance..."
if ! gcloud sql instances describe "$DB_INSTANCE_NAME" >/dev/null 2>&1; then
    # Generate a random root password instead of using a hardcoded one
    ROOT_PASSWORD=$(openssl rand -base64 24)
    echo "Creating Cloud SQL instance (Tier: db-f1-micro)... this may take 10-15 minutes."
    gcloud sql instances create "$DB_INSTANCE_NAME" \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region="$REGION" \
        --root-password="$ROOT_PASSWORD"
    STORE_ROOT_PASSWORD=true
else
    echo "Cloud SQL instance $DB_INSTANCE_NAME already exists."
    STORE_ROOT_PASSWORD=false
fi

echo "Creating database '$DB_NAME'..."
gcloud sql databases create "$DB_NAME" --instance="$DB_INSTANCE_NAME" || true

echo "Creating user '$DB_USER'..."
# Only generate a new password if the user is being newly created.
# If the user already exists, read the existing password from Secret Manager
# to avoid breaking active connections with a password change.
DB_PASSWORD=$(openssl rand -base64 24)
if gcloud sql users create "$DB_USER" --instance="$DB_INSTANCE_NAME" --password="$DB_PASSWORD" 2>/dev/null; then
    echo "User $DB_USER created with new password."
    NEW_DB_USER=true
else
    echo "User $DB_USER already exists. Reading existing password from Secret Manager..."
    DB_PASSWORD=$(gcloud secrets versions access latest --secret="VERITAS_DB_PASSWORD" 2>/dev/null) || {
        echo "WARNING: Could not read existing password from Secret Manager."
        echo "The user exists but no stored password was found. You may need to reset it manually."
    }
    NEW_DB_USER=false
fi

# ==============================================================================
# 4. Secrets Management
# ==============================================================================
echo "Configuring Secrets..."

# Helper to create/update secret
create_secret() {
    local name=$1
    local value=$2
    if ! gcloud secrets describe "$name" >/dev/null 2>&1; then
        gcloud secrets create "$name" --replication-policy="automatic"
    fi
    echo -n "$value" | gcloud secrets versions add "$name" --data-file=-
}

# 1. Store DB password (only if user was newly created)
if [ "$NEW_DB_USER" = "true" ]; then
    create_secret "VERITAS_DB_PASSWORD" "$DB_PASSWORD"
    echo "Secret VERITAS_DB_PASSWORD updated with new password."
else
    echo "Skipping DB password secret update (user already existed)."
fi

# 2. Store root password (only if instance was newly created)
if [ "$STORE_ROOT_PASSWORD" = "true" ]; then
    create_secret "VERITAS_DB_ROOT_PASSWORD" "$ROOT_PASSWORD"
    echo "Secret VERITAS_DB_ROOT_PASSWORD stored."
fi

# 3. Construct and Store Database URL
# Asyncpg format: postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/project:region:instance
INSTANCE_CONNECTION_NAME="${PROJECT_ID}:${REGION}:${DB_INSTANCE_NAME}"
DB_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${INSTANCE_CONNECTION_NAME}"

if [ "$NEW_DB_USER" = "true" ]; then
    create_secret "VERITAS_DB_URL" "$DB_URL"
    echo "Secret VERITAS_DB_URL updated."
else
    echo "Skipping DB URL secret update (using existing credentials)."
fi

# 4. Read agent config from backend/.env
ENV_FILE="${BACKEND_DIR}/.env"
read_env() { grep "^$1=" "$ENV_FILE" 2>/dev/null | sed "s/^$1=//" || true; }
if [ -f "$ENV_FILE" ]; then
    GEMINI_API_KEY=$(read_env GEMINI_API_KEY)
    GEMINI_PRO_MODEL=$(read_env GEMINI_PRO_MODEL)
    GEMINI_FLASH_MODEL=$(read_env GEMINI_FLASH_MODEL)
    GOOGLE_GENAI_USE_VERTEXAI=$(read_env GOOGLE_GENAI_USE_VERTEXAI)
    VERITAS_AGENT_MODE=$(read_env VERITAS_AGENT_MODE)
    NUMERIC_VALIDATION_AGENT_MODE=$(read_env NUMERIC_VALIDATION_AGENT_MODE)
fi
if [ -z "$GEMINI_API_KEY" ]; then
    read -rp "Enter GEMINI_API_KEY (not found in .env): " GEMINI_API_KEY
fi
if [ -n "$GEMINI_API_KEY" ]; then
    create_secret "VERITAS_GEMINI_API_KEY" "$GEMINI_API_KEY"
    echo "Secret VERITAS_GEMINI_API_KEY stored."
else
    echo "WARNING: No GEMINI_API_KEY provided. Agent pipeline will not work without it."
fi

# 5. Grant Cloud Run service account access to secrets
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Granting Secret Manager access to $SA_EMAIL..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --quiet

# ==============================================================================
# 6. Build & Deploy to Cloud Run
# ==============================================================================
echo "Building and Deploying to Cloud Run..."

# Create Artifact Registry repo if not exists
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" >/dev/null 2>&1; then
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Docker repository for Veritas AI"
fi

IMAGE_URL="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME"

# Build and push container
echo "Submitting build to Cloud Build..."

# Ensure we are in the backend directory
cd "$BACKEND_DIR"

gcloud builds submit --tag "$IMAGE_URL" .

echo "Deploying Container..."
# Build env vars dynamically — only include overrides if set in .env
# Auto-detect frontend URL for CORS if frontend is already deployed
FRONTEND_URL=$(gcloud run services describe "veritas-ai-frontend${SUFFIX}" --region "$REGION" --format='value(status.url)' 2>/dev/null || true)
ALLOWED_ORIGINS="${FRONTEND_URL:-*}"
ENV_VARS="GCS_BUCKET=${BUCKET_NAME},DEBUG=false,ALLOWED_ORIGINS=${ALLOWED_ORIGINS}"
[ -n "$GOOGLE_GENAI_USE_VERTEXAI" ] && ENV_VARS="${ENV_VARS},GOOGLE_GENAI_USE_VERTEXAI=${GOOGLE_GENAI_USE_VERTEXAI}"
[ -n "$GEMINI_PRO_MODEL" ] && ENV_VARS="${ENV_VARS},GEMINI_PRO_MODEL=${GEMINI_PRO_MODEL}"
[ -n "$GEMINI_FLASH_MODEL" ] && ENV_VARS="${ENV_VARS},GEMINI_FLASH_MODEL=${GEMINI_FLASH_MODEL}"
[ -n "$VERITAS_AGENT_MODE" ] && ENV_VARS="${ENV_VARS},VERITAS_AGENT_MODE=${VERITAS_AGENT_MODE}"
[ -n "$NUMERIC_VALIDATION_AGENT_MODE" ] && ENV_VARS="${ENV_VARS},NUMERIC_VALIDATION_AGENT_MODE=${NUMERIC_VALIDATION_AGENT_MODE}"

gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_URL" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --timeout=3600 \
    --add-cloudsql-instances="$INSTANCE_CONNECTION_NAME" \
    --set-secrets="DATABASE_URL=VERITAS_DB_URL:latest,GEMINI_API_KEY=VERITAS_GEMINI_API_KEY:latest" \
    --set-env-vars="$ENV_VARS"

echo ""
echo "✅ Deployment Complete!"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)')
echo "Service URL: $SERVICE_URL"
if [ "$ALLOWED_ORIGINS" = "*" ]; then
    echo ""
    echo "⚠️  ALLOWED_ORIGINS is set to '*' (frontend not yet deployed)."
    echo "  It will be set automatically when you deploy the frontend."
fi

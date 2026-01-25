#!/bin/bash
set -e

# Configuration
REGION="us-central1"
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="veritas-ai-backend"
DB_INSTANCE_NAME="veritas-ai-db-primary"
DB_NAME="veritas"
DB_USER="veritas_app"
BUCKET_NAME="${PROJECT_ID}-docs-${REGION}"
REPO_NAME="veritas-ai-repo"

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
    echo "Creating Cloud SQL instance (Tier: db-f1-micro)... this may take 10-15 minutes."
    gcloud sql instances create "$DB_INSTANCE_NAME" \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region="$REGION" \
        --root-password="temporary-root-password-change-me" 
else
    echo "Cloud SQL instance $DB_INSTANCE_NAME already exists."
fi

echo "Creating database '$DB_NAME'..."
gcloud sql databases create "$DB_NAME" --instance="$DB_INSTANCE_NAME" || true

echo "Creating user '$DB_USER'..."
# Generate random password
DB_PASSWORD=$(openssl rand -base64 24)
gcloud sql users create "$DB_USER" --instance="$DB_INSTANCE_NAME" --password="$DB_PASSWORD" || {
    echo "User $DB_USER might already exist. Updating password..."
    gcloud sql users set-password "$DB_USER" --instance="$DB_INSTANCE_NAME" --password="$DB_PASSWORD"
}

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

# 1. Store Password
create_secret "VERITAS_DB_PASSWORD" "$DB_PASSWORD"

# 2. Construct and Store Database URL
# Asyncpg format: postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/project:region:instance
INSTANCE_CONNECTION_NAME="${PROJECT_ID}:${REGION}:${DB_INSTANCE_NAME}"
DB_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${INSTANCE_CONNECTION_NAME}"

create_secret "VERITAS_DB_URL" "$DB_URL"

echo "Secrets VERITAS_DB_PASSWORD and VERITAS_DB_URL updated."

# 3. Grant Cloud Run service account access to secrets
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Granting Secret Manager access to $SA_EMAIL..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --quiet

# ==============================================================================
# 5. Build & Deploy to Cloud Run
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

gcloud builds submit --tag "$IMAGE_URL" .

echo "Deploying Container..."
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_URL" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --add-cloudsql-instances="$INSTANCE_CONNECTION_NAME" \
    --set-secrets="DATABASE_URL=VERITAS_DB_URL:latest" \
    --set-env-vars="GCS_BUCKET=${BUCKET_NAME},DEBUG=true"

echo "✅ Deployment Complete!"
echo "Service URL: $(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')"

#!/bin/bash

# Deploy GCP Secret Manager rotation infrastructure
# This script sets up Cloud Functions and Cloud Scheduler for automated secret rotation

set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
REGION=${GCP_REGION:-"us-central1"}
FUNCTION_NAME="rotate-secret"
VALIDATION_FUNCTION_NAME="validate-secrets"
BULK_FUNCTION_NAME="bulk-rotate-secrets"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying GCP Secret Manager rotation infrastructure...${NC}"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Not authenticated with gcloud. Please run 'gcloud auth login' first.${NC}"
    exit 1
fi

# Set the project
echo -e "${YELLOW}📋 Setting project to: ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Create secrets in Secret Manager (if they don't exist)
echo -e "${YELLOW}🔐 Creating secrets in Secret Manager...${NC}"

# Function to create secret if it doesn't exist
create_secret_if_not_exists() {
    local secret_name=$1
    local initial_value=$2

    if ! gcloud secrets describe ${secret_name} --project=${PROJECT_ID} &> /dev/null; then
        echo "Creating secret: ${secret_name}"
        echo -n "${initial_value}" | gcloud secrets create ${secret_name} \
            --data-file=- \
            --project=${PROJECT_ID} \
            --replication-policy="automatic"
    else
        echo "Secret already exists: ${secret_name}"
    fi
}

# Create production secrets
create_secret_if_not_exists "prod-jwt-secret-key" "$(openssl rand -base64 32)"
create_secret_if_not_exists "prod-database-password" "$(openssl rand -base64 32)"
create_secret_if_not_exists "prod-redis-password" "$(openssl rand -base64 32)"
create_secret_if_not_exists "prod-huggingface-token" "your-huggingface-token-here"

# Create staging secrets
create_secret_if_not_exists "staging-jwt-secret-key" "$(openssl rand -base64 32)"
create_secret_if_not_exists "staging-database-password" "$(openssl rand -base64 32)"
create_secret_if_not_exists "staging-redis-password" "$(openssl rand -base64 32)"
create_secret_if_not_exists "staging-huggingface-token" "your-huggingface-token-here"

# Deploy Cloud Functions
echo -e "${YELLOW}☁️  Deploying Cloud Functions...${NC}"

# Deploy main rotation function
gcloud functions deploy ${FUNCTION_NAME} \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --source ./cloud-functions/secret-rotation \
    --entry-point rotate_secret \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --memory 256MB \
    --timeout 300s \
    --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID}

# Deploy validation function
gcloud functions deploy ${VALIDATION_FUNCTION_NAME} \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --source ./cloud-functions/secret-rotation \
    --entry-point validate_secrets \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --memory 256MB \
    --timeout 180s \
    --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID}

# Deploy bulk rotation function
gcloud functions deploy ${BULK_FUNCTION_NAME} \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --source ./cloud-functions/secret-rotation \
    --entry-point bulk_rotate_secrets \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --memory 512MB \
    --timeout 600s \
    --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID}

# Create Cloud Scheduler jobs
echo -e "${YELLOW}⏰ Creating Cloud Scheduler jobs...${NC}"

# Function to create scheduler job
create_scheduler_job() {
    local job_name=$1
    local schedule=$2
    local secret_id=$3
    local rotation_type=$4

    # Check if job already exists
    if gcloud scheduler jobs describe ${job_name} --location=${REGION} --project=${PROJECT_ID} &> /dev/null; then
        echo "Scheduler job already exists: ${job_name}"
        return
    fi

    echo "Creating scheduler job: ${job_name}"
    gcloud scheduler jobs create http ${job_name} \
        --location=${REGION} \
        --schedule="${schedule}" \
        --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/${FUNCTION_NAME}" \
        --http-method=POST \
        --headers="Content-Type=application/json" \
        --message-body="{\"secret_id\":\"${secret_id}\",\"environment\":\"prod\",\"rotation_type\":\"${rotation_type}\"}" \
        --time-zone="UTC" \
        --project=${PROJECT_ID}
}

# Create rotation schedules
create_scheduler_job "jwt-secret-rotation" "0 2 1 * *" "jwt-secret-key" "jwt"
create_scheduler_job "database-password-rotation" "0 3 1 */3 *" "database-password" "password"
create_scheduler_job "redis-password-rotation" "0 4 1 */2 *" "redis-password" "password"
create_scheduler_job "huggingface-token-rotation" "0 5 1 */6 *" "huggingface-token" "token"

# Create validation schedule
if ! gcloud scheduler jobs describe secret-validation --location=${REGION} --project=${PROJECT_ID} &> /dev/null; then
    echo "Creating validation scheduler job"
    gcloud scheduler jobs create http secret-validation \
        --location=${REGION} \
        --schedule="0 6 * * *" \
        --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/${VALIDATION_FUNCTION_NAME}" \
        --http-method=POST \
        --headers="Content-Type=application/json" \
        --message-body='{"environment":"prod"}' \
        --time-zone="UTC" \
        --project=${PROJECT_ID}
fi

# Set up IAM permissions
echo -e "${YELLOW}🔑 Setting up IAM permissions...${NC}"

# Get the Cloud Functions service account
FUNCTION_SA="${PROJECT_ID}@appspot.gserviceaccount.com"

# Grant Secret Manager access to Cloud Functions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${FUNCTION_SA}" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${FUNCTION_SA}" \
    --role="roles/secretmanager.secretVersionManager"

# Grant Cloud Scheduler access to invoke Cloud Functions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:service-$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')@gcp-sa-cloudscheduler.iam.gserviceaccount.com" \
    --role="roles/cloudfunctions.invoker"

# Test the setup
echo -e "${YELLOW}🧪 Testing the setup...${NC}"

# Test secret validation
echo "Testing secret validation..."
gcloud functions call ${VALIDATION_FUNCTION_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --data='{"environment":"prod"}'

echo -e "${GREEN}✅ GCP Secret Manager rotation infrastructure deployed successfully!${NC}"
echo -e "${GREEN}📋 Summary:${NC}"
echo -e "  • Project: ${PROJECT_ID}"
echo -e "  • Region: ${REGION}"
echo -e "  • Cloud Functions deployed: ${FUNCTION_NAME}, ${VALIDATION_FUNCTION_NAME}, ${BULK_FUNCTION_NAME}"
echo -e "  • Cloud Scheduler jobs created for automated rotation"
echo -e "  • Secrets created in Secret Manager"
echo -e "  • IAM permissions configured"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo -e "  1. Update your application to use the new secret-aware configuration"
echo -e "  2. Test secret retrieval in your application"
echo -e "  3. Monitor the Cloud Scheduler jobs and Cloud Functions logs"
echo -e "  4. Update HuggingFace tokens with real values"
echo ""
echo -e "${YELLOW}🔍 Useful commands:${NC}"
echo -e "  • View secrets: gcloud secrets list --project=${PROJECT_ID}"
echo -e "  • View scheduler jobs: gcloud scheduler jobs list --location=${REGION} --project=${PROJECT_ID}"
echo -e "  • View function logs: gcloud functions logs read ${FUNCTION_NAME} --region=${REGION} --project=${PROJECT_ID}"
echo -e "  • Manual rotation: gcloud functions call ${FUNCTION_NAME} --region=${REGION} --project=${PROJECT_ID} --data='{\"secret_id\":\"jwt-secret-key\",\"environment\":\"prod\"}'"

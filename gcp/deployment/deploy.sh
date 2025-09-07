#!/bin/bash
# GCP Deployment Script for DevCycle API
# This script deploys the DevCycle API to GCP using Cloud Run or Compute Engine

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
SERVICE_NAME="devcycle-api"
REGION="${GCP_REGION:-us-central1}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
TAG="${TAG:-latest}"
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-cloud-run}"  # cloud-run or compute-engine

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi

    log_info "All dependencies are installed."
}

# Authenticate with GCP
authenticate() {
    log_info "Authenticating with GCP..."
    gcloud auth login
    gcloud config set project ${PROJECT_ID}
    gcloud auth configure-docker
    log_info "Authentication complete."
}

# Build and push Docker image
build_and_push() {
    log_info "Building Docker image..."
    docker build -f gcp/deployment/Dockerfile -t ${IMAGE_NAME}:${TAG} .

    log_info "Pushing image to GCR..."
    docker push ${IMAGE_NAME}:${TAG}
    log_info "Image pushed successfully."
}

# Deploy to Cloud Run
deploy_cloud_run() {
    log_info "Deploying to Cloud Run..."

    gcloud run deploy ${SERVICE_NAME} \
        --image ${IMAGE_NAME}:${TAG} \
        --platform managed \
        --region ${REGION} \
        --allow-unauthenticated \
        --port 8000 \
        --memory 2Gi \
        --cpu 2 \
        --max-instances 100 \
        --min-instances 1 \
        --timeout 300 \
        --concurrency 100 \
        --set-env-vars "ENVIRONMENT=production,API_HOST=0.0.0.0,API_PORT=8000,API_GCP_LOAD_BALANCER_ENABLED=true,API_TRUST_PROXY=true" \
        --set-secrets "DB_HOST=devcycle-secrets:db-host,DB_PASSWORD=devcycle-secrets:db-password,SECURITY_SECRET_KEY=devcycle-secrets:secret-key,REDIS_HOST=devcycle-secrets:redis-host,REDIS_PASSWORD=devcycle-secrets:redis-password,HF_TOKEN=devcycle-secrets:hf-token"

    log_info "Cloud Run deployment complete."
}

# Deploy to Compute Engine (GKE)
deploy_compute_engine() {
    log_info "Deploying to Compute Engine (GKE)..."

    # Apply Kubernetes manifests
    kubectl apply -f gcp/deployment/compute-engine.yaml
    kubectl apply -f gcp/deployment/load-balancer.yaml

    # Wait for deployment to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/devcycle-api-deployment

    log_info "Compute Engine deployment complete."
}

# Create secrets
create_secrets() {
    log_info "Creating secrets..."

    # Check if secrets already exist
    if gcloud secrets describe devcycle-secrets &> /dev/null; then
        log_warn "Secrets already exist. Skipping creation."
        return
    fi

    # Create secret with placeholder values
    echo -n "your-db-host" | gcloud secrets create devcycle-secrets --data-file=-
    echo -n "your-db-password" | gcloud secrets versions add devcycle-secrets --data-file=-
    echo -n "your-secret-key" | gcloud secrets versions add devcycle-secrets --data-file=-
    echo -n "your-redis-host" | gcloud secrets versions add devcycle-secrets --data-file=-
    echo -n "your-redis-password" | gcloud secrets versions add devcycle-secrets --data-file=-
    echo -n "your-hf-token" | gcloud secrets versions add devcycle-secrets --data-file=-

    log_info "Secrets created. Please update them with actual values."
}

# Main deployment function
main() {
    log_info "Starting DevCycle API deployment to GCP..."
    log_info "Project ID: ${PROJECT_ID}"
    log_info "Service Name: ${SERVICE_NAME}"
    log_info "Region: ${REGION}"
    log_info "Deployment Type: ${DEPLOYMENT_TYPE}"

    check_dependencies
    authenticate
    create_secrets
    build_and_push

    case ${DEPLOYMENT_TYPE} in
        "cloud-run")
            deploy_cloud_run
            ;;
        "compute-engine")
            deploy_compute_engine
            ;;
        *)
            log_error "Invalid deployment type: ${DEPLOYMENT_TYPE}"
            log_error "Valid options: cloud-run, compute-engine"
            exit 1
            ;;
    esac

    log_info "Deployment complete!"
    log_info "Service URL: https://${SERVICE_NAME}-${PROJECT_ID}.${REGION}.run.app"
}

# Run main function
main "$@"

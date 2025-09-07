#!/bin/bash

# Kibana Setup Script for DevCycle Security Monitoring
# This script sets up Kibana with security monitoring dashboards and index patterns

set -e

# Configuration
KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"
ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-http://localhost:9200}"
INDEX_PATTERN="devcycle-security-*"
DASHBOARD_ID="security-monitoring-dashboard"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
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

    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        log_warn "jq is not installed. Some features may not work properly"
    fi

    log_info "Dependencies check completed"
}

# Wait for Kibana to be ready
wait_for_kibana() {
    log_info "Waiting for Kibana to be ready..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s "$KIBANA_URL/api/status" > /dev/null 2>&1; then
            log_info "Kibana is ready"
            return 0
        fi

        log_info "Attempt $attempt/$max_attempts: Kibana not ready yet, waiting 10 seconds..."
        sleep 10
        ((attempt++))
    done

    log_error "Kibana did not become ready within expected time"
    exit 1
}

# Wait for Elasticsearch to be ready
wait_for_elasticsearch() {
    log_info "Waiting for Elasticsearch to be ready..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s "$ELASTICSEARCH_URL/_cluster/health" > /dev/null 2>&1; then
            log_info "Elasticsearch is ready"
            return 0
        fi

        log_info "Attempt $attempt/$max_attempts: Elasticsearch not ready yet, waiting 10 seconds..."
        sleep 10
        ((attempt++))
    done

    log_error "Elasticsearch did not become ready within expected time"
    exit 1
}

# Create index pattern
create_index_pattern() {
    log_info "Creating index pattern: $INDEX_PATTERN"

    local index_pattern_data='{
        "attributes": {
            "title": "'$INDEX_PATTERN'",
            "timeFieldName": "@timestamp"
        }
    }'

    local response=$(curl -s -X POST \
        "$KIBANA_URL/api/saved_objects/index-pattern" \
        -H "Content-Type: application/json" \
        -H "kbn-xsrf: true" \
        -d "$index_pattern_data")

    if echo "$response" | grep -q '"id"'; then
        log_info "Index pattern created successfully"
    else
        log_warn "Index pattern may already exist or creation failed"
        echo "Response: $response"
    fi
}

# Import dashboard
import_dashboard() {
    log_info "Importing security monitoring dashboard..."

    local dashboard_file="kibana/security-dashboard.json"

    if [ ! -f "$dashboard_file" ]; then
        log_error "Dashboard file not found: $dashboard_file"
        exit 1
    fi

    local response=$(curl -s -X POST \
        "$KIBANA_URL/api/saved_objects/_import" \
        -H "Content-Type: application/json" \
        -H "kbn-xsrf: true" \
        --data-binary @"$dashboard_file")

    if echo "$response" | grep -q '"success"'; then
        log_info "Dashboard imported successfully"
    else
        log_warn "Dashboard import may have failed or already exists"
        echo "Response: $response"
    fi
}

# Create sample data
create_sample_data() {
    log_info "Creating sample security data..."

    local sample_events=(
        '{"@timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'","event_type":"auth_success","severity":"low","user_id":"user_123","ip_address":"192.168.1.100","user_agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","service":"devcycle-api","environment":"production","security_event":true,"event_category":"security","severity_level":1}'
        '{"@timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'","event_type":"auth_failure","severity":"medium","ip_address":"192.168.1.101","user_agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36","service":"devcycle-api","environment":"production","security_event":true,"event_category":"security","severity_level":2}'
        '{"@timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'","event_type":"rate_limit_exceeded","severity":"medium","ip_address":"192.168.1.102","service":"devcycle-api","environment":"production","security_event":true,"event_category":"security","severity_level":2}'
        '{"@timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'","event_type":"suspicious_activity","severity":"high","user_id":"user_456","ip_address":"192.168.1.103","service":"devcycle-api","environment":"production","security_event":true,"event_category":"security","severity_level":3}'
        '{"@timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'","event_type":"access_denied","severity":"medium","user_id":"user_789","ip_address":"192.168.1.104","service":"devcycle-api","environment":"production","security_event":true,"event_category":"security","severity_level":2}'
    )

    for event in "${sample_events[@]}"; do
        curl -s -X POST \
            "$ELASTICSEARCH_URL/devcycle-security-$(date +%Y.%m.%d)/_doc" \
            -H "Content-Type: application/json" \
            -d "$event" > /dev/null
    done

    log_info "Sample data created"
}

# Setup Kibana space
setup_kibana_space() {
    log_info "Setting up Kibana space for security monitoring..."

    # Create a dedicated space for security monitoring
    local space_data='{
        "id": "security-monitoring",
        "name": "Security Monitoring",
        "description": "Space dedicated to security monitoring and audit logging"
    }'

    local response=$(curl -s -X POST \
        "$KIBANA_URL/api/spaces/space" \
        -H "Content-Type: application/json" \
        -H "kbn-xsrf: true" \
        -d "$space_data")

    if echo "$response" | grep -q '"id"'; then
        log_info "Kibana space created successfully"
    else
        log_warn "Kibana space may already exist or creation failed"
        echo "Response: $response"
    fi
}

# Main setup function
main() {
    log_info "Starting Kibana setup for DevCycle Security Monitoring"

    # Check dependencies
    check_dependencies

    # Wait for services
    wait_for_elasticsearch
    wait_for_kibana

    # Setup Kibana
    setup_kibana_space
    create_index_pattern
    import_dashboard

    # Create sample data
    create_sample_data

    log_info "Kibana setup completed successfully!"
    log_info "Dashboard URL: $KIBANA_URL/app/dashboards#/view/$DASHBOARD_ID"
    log_info "Index Pattern: $INDEX_PATTERN"
    log_info "Elasticsearch URL: $ELASTICSEARCH_URL"

    echo ""
    log_info "Next steps:"
    echo "1. Access Kibana at: $KIBANA_URL"
    echo "2. Navigate to the Security Monitoring dashboard"
    echo "3. Configure your DevCycle API to send logs to Elasticsearch"
    echo "4. Set up log shipping from your application to Elasticsearch"
    echo "5. Configure alerts and notifications in Kibana"
}

# Run main function
main "$@"

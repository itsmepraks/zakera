#!/bin/bash
# Production deployment script
# Usage: ./deploy.sh [staging|production]

set -e

ENVIRONMENT=${1:-staging}
REGION="us-east-1"
CLUSTER="zakera-${ENVIRONMENT}"
SERVICE="zakera-api"
TASK_FAMILY="zakera-${ENVIRONMENT}"

echo "========================================"
echo "Deploying Zakera to ${ENVIRONMENT}"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    log_error "Invalid environment. Use 'staging' or 'production'"
    exit 1
fi

# Check required tools
for tool in aws jq docker; do
    if ! command -v $tool &> /dev/null; then
        log_error "$tool is required but not installed"
        exit 1
    fi
done

log_info "Checking AWS credentials..."
aws sts get-caller-identity > /dev/null || {
    log_error "AWS credentials not configured"
    exit 1
}

# Get current task definition
log_info "Fetching current task definition..."
CURRENT_TASK=$(aws ecs describe-task-definition \
    --task-definition $TASK_FAMILY \
    --region $REGION \
    --query 'taskDefinition' \
    --output json)

# Get new image tag
IMAGE_TAG=${GITHUB_SHA:-latest}
IMAGE="ghcr.io/itsmepraks/zakera:${IMAGE_TAG}"

log_info "Using image: ${IMAGE}"

# Update task definition with new image
NEW_TASK=$(echo $CURRENT_TASK | jq --arg IMAGE "$IMAGE" '
    .containerDefinitions[0].image = $IMAGE |
    del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)
')

# Register new task definition
log_info "Registering new task definition..."
NEW_TASK_ARN=$(aws ecs register-task-definition \
    --region $REGION \
    --cli-input-json "$NEW_TASK" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

log_info "New task definition: ${NEW_TASK_ARN}"

# Update service
log_info "Updating ECS service..."
aws ecs update-service \
    --region $REGION \
    --cluster $CLUSTER \
    --service $SERVICE \
    --task-definition $NEW_TASK_ARN \
    --force-new-deployment \
    > /dev/null

log_info "Waiting for service to stabilize..."
aws ecs wait services-stable \
    --region $REGION \
    --cluster $CLUSTER \
    --services $SERVICE

log_info "Deployment completed successfully!"

# Get service status
RUNNING_COUNT=$(aws ecs describe-services \
    --region $REGION \
    --cluster $CLUSTER \
    --services $SERVICE \
    --query 'services[0].runningCount' \
    --output text)

log_info "Running tasks: ${RUNNING_COUNT}"

echo ""
echo "========================================"
echo "Deployment Summary"
echo "========================================"
echo "Environment: ${ENVIRONMENT}"
echo "Image: ${IMAGE}"
echo "Task Definition: ${NEW_TASK_ARN}"
echo "Running Tasks: ${RUNNING_COUNT}"
echo "========================================"

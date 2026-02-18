#!/bin/bash
# Deploy Searchable PDF to AWS App Runner
# Prerequisites: AWS CLI configured, Docker, NANONETS_API_KEY set
# Usage: NANONETS_API_KEY=your_key ./deploy/deploy.sh
set -e

REGION="${AWS_REGION:-us-east-1}"
ECR_REPO="searchable-pdf"
ECR_URI="906016811878.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"
APP_RUNNER_ECR_ACCESS_ARN="arn:aws:iam::906016811878:role/apprunner-ecr-access"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$NANONETS_API_KEY" ]; then
  echo "Error: NANONETS_API_KEY must be set."
  echo "Usage: NANONETS_API_KEY=your_key $0"
  exit 1
fi

echo "=== Building Docker image ==="
cd "$SCRIPT_DIR/.." && docker build -t ${ECR_REPO}:latest .

echo "=== Logging into ECR ==="
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin 906016811878.dkr.ecr.${REGION}.amazonaws.com

echo "=== Pushing to ECR ==="
docker tag ${ECR_REPO}:latest ${ECR_URI}:latest
docker push ${ECR_URI}:latest

echo "=== Checking for existing App Runner service ==="
SERVICE_ARN=$(aws apprunner list-services --region $REGION --query "ServiceSummaryList[?ServiceName=='searchable-pdf'].ServiceArn" --output text 2>/dev/null || true)

if [ -n "$SERVICE_ARN" ] && [ "$SERVICE_ARN" != "None" ]; then
  echo "=== Starting deployment of existing service ==="
  aws apprunner start-deployment --service-arn "$SERVICE_ARN" --region $REGION
  echo "Deployment started!"
else
  echo "=== Creating new App Runner service ==="
  # Create temp config with actual API key
  TMP_JSON=$(mktemp)
  jq --arg key "$NANONETS_API_KEY" \
    '.SourceConfiguration.ImageRepository.ImageConfiguration.RuntimeEnvironmentVariables.NANONETS_API_KEY = $key' \
    "$SCRIPT_DIR/apprunner-create.json" > "$TMP_JSON"

  aws apprunner create-service --cli-input-json "file://$TMP_JSON" --region $REGION
  rm -f "$TMP_JSON"
  echo "Service created!"
fi

echo ""
sleep 3
aws apprunner list-services --region $REGION --query "ServiceSummaryList[?ServiceName=='searchable-pdf'].[ServiceUrl,Status]" --output table

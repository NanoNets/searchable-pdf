#!/bin/bash
# Create App Runner service (production with Secrets Manager) - no Docker build
# Use after image is in ECR (e.g. from GitHub Actions)
# Usage: NANONETS_SECRET_ARN=arn:... ./deploy/create-service-only.sh
set -e

REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$NANONETS_SECRET_ARN" ]; then
  echo "Error: NANONETS_SECRET_ARN must be set."
  exit 1
fi

SERVICE_ARN=$(aws apprunner list-services --region $REGION --query "ServiceSummaryList[?ServiceName=='searchable-pdf'].ServiceArn" --output text 2>/dev/null || true)

if [ -n "$SERVICE_ARN" ] && [ "$SERVICE_ARN" != "None" ]; then
  echo "Service already exists. Starting deployment..."
  aws apprunner start-deployment --service-arn "$SERVICE_ARN" --region $REGION
else
  echo "Creating App Runner service..."
  TMP_JSON=$(mktemp)
  jq --arg arn "$NANONETS_SECRET_ARN" \
    '.SourceConfiguration.ImageRepository.ImageConfiguration.RuntimeEnvironmentSecrets.NANONETS_API_KEY = $arn' \
    "$SCRIPT_DIR/apprunner-create-production.json" > "$TMP_JSON"
  aws apprunner create-service --cli-input-json "file://$TMP_JSON" --region $REGION
  rm -f "$TMP_JSON"
  echo "Service created!"
fi

sleep 3
aws apprunner list-services --region $REGION --query "ServiceSummaryList[?ServiceName=='searchable-pdf'].[ServiceUrl,Status]" --output table

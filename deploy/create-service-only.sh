#!/bin/bash
# Create App Runner service (production) - no Docker build
# Use after image is in ECR (e.g. from GitHub Actions)
# Usage: NANONETS_SECRET_ARN=arn:... ./deploy/create-service-only.sh
# Or: NANONETS_API_KEY=your_key ./deploy/create-service-only.sh  (fetches from Secrets Manager)
set -e

REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Get API key: from Secrets Manager ARN or direct env
if [ -n "$NANONETS_SECRET_ARN" ]; then
  echo "Fetching API key from Secrets Manager..."
  NANONETS_API_KEY=$(aws secretsmanager get-secret-value --secret-id "$NANONETS_SECRET_ARN" --region $REGION --query SecretString --output text)
elif [ -z "$NANONETS_API_KEY" ]; then
  echo "Error: NANONETS_SECRET_ARN or NANONETS_API_KEY must be set."
  exit 1
fi

SERVICE_ARN=$(aws apprunner list-services --region $REGION --query "ServiceSummaryList[?ServiceName=='searchable-pdf'].ServiceArn" --output text 2>/dev/null || true)

if [ -n "$SERVICE_ARN" ] && [ "$SERVICE_ARN" != "None" ]; then
  echo "Service already exists. Starting deployment..."
  aws apprunner start-deployment --service-arn "$SERVICE_ARN" --region $REGION
else
  echo "Creating App Runner service..."
  TMP_JSON=$(mktemp)
  jq --arg key "$NANONETS_API_KEY" \
    '.SourceConfiguration.ImageRepository.ImageConfiguration.RuntimeEnvironmentVariables.NANONETS_API_KEY = $key' \
    "$SCRIPT_DIR/apprunner-create.json" > "$TMP_JSON"
  aws apprunner create-service --cli-input-json "file://$TMP_JSON" --region $REGION
  rm -f "$TMP_JSON"
  echo "Service created!"
fi

sleep 3
aws apprunner list-services --region $REGION --query "ServiceSummaryList[?ServiceName=='searchable-pdf'].[ServiceUrl,Status]" --output table

#!/bin/bash
# Create NANONETS_API_KEY in AWS Secrets Manager for production App Runner
# Usage: NANONETS_API_KEY=your_key ./deploy/create-secret.sh
set -e

REGION="${AWS_REGION:-us-east-1}"
SECRET_NAME="searchable-pdf/nanonets-api-key"

if [ -z "$NANONETS_API_KEY" ]; then
  echo "Error: NANONETS_API_KEY must be set."
  echo "Usage: NANONETS_API_KEY=your_key $0"
  exit 1
fi

echo "Creating secret in AWS Secrets Manager..."
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" 2>/dev/null; then
  echo "Secret already exists. Updating..."
  ARN=$(aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" --query 'ARN' --output text)
  aws secretsmanager put-secret-value \
    --secret-id "$SECRET_NAME" \
    --secret-string "$NANONETS_API_KEY" \
    --region "$REGION" > /dev/null
  echo "Updated. ARN: $ARN"
else
  ARN=$(aws secretsmanager create-secret \
    --name "$SECRET_NAME" \
    --secret-string "$NANONETS_API_KEY" \
    --region "$REGION" \
    --output json | jq -r '.ARN')
  echo "Created. ARN: $ARN"
fi
echo ""
echo "Use this for production deploy:"
echo "  NANONETS_SECRET_ARN=$ARN ./deploy/deploy.sh --production"

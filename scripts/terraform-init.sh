#!/bin/bash
set -e

echo "Initializing Terraform for AI DevOps Platform..."
echo "===================================================="

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"

echo "Using AWS Account ID: $AWS_ACCOUNT_ID"
echo "Using AWS Region: $AWS_REGION"

# Create the terraform.tfvars file to ensure it's correct
cat > infrastructure/terraform/terraform.tfvars << EOF
aws_region     = "$AWS_REGION"
environment    = "dev"
aws_account_id = "$AWS_ACCOUNT_ID"
project_name   = "ai-devops-platform"
EOF
echo "✅ Wrote terraform.tfvars file"

# Initialize Terraform directly.
# Terraform's own init process is the most reliable way to verify backend access.
cd infrastructure/terraform
terraform init \
  -backend-config="bucket=ai-devops-platform-tfstate-$AWS_ACCOUNT_ID" \
  -backend-config="region=$AWS_REGION" \
  -backend-config="encrypt=true" \
  -reconfigure

echo ""
echo "✅ Terraform initialized successfully!"
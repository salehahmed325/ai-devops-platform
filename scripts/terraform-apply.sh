#!/bin/bash
set -e

echo "🚀 Applying Terraform configuration..."
echo "======================================"

cd infrastructure/terraform

# Function to import existing resources
import_existing_resources() {
    local AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    echo "🔄 Attempting to import existing resources..."
    
    # Try to import S3 bucket if it exists
    if aws s3 ls "s3://ai-devops-platform-tfstate-$AWS_ACCOUNT_ID" --region us-east-1 2>/dev/null; then
        echo "📦 Importing existing S3 bucket..."
        terraform import aws_s3_bucket.tfstate ai-devops-platform-tfstate-$AWS_ACCOUNT_ID 2>/dev/null || true
    fi
    
    # Try to import IAM policy if it exists
    if aws iam list-policies --query "Policies[?PolicyName=='AIDevOpsPlatformPolicy'].Arn" --output text 2>/dev/null | grep -q arn; then
        echo "🔐 Importing existing IAM policy..."
        POLICY_ARN=$(aws iam list-policies --query "Policies[?PolicyName=='AIDevOpsPlatformPolicy'].Arn" --output text)
        terraform import module.iam.aws_iam_policy.ai_devops_policy "$POLICY_ARN" 2>/dev/null || true
    fi
}

# First, try to import any existing resources
import_existing_resources

# Then plan
echo "📋 Generating Terraform plan..."
terraform plan -out=tfplan

# Ask for confirmation
read -p "Do you want to apply this plan? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Operation cancelled."
    exit 1
fi

# Apply
echo "🛠️  Applying Terraform configuration..."
terraform apply tfplan

# Output the results
echo ""
echo "✅ Terraform apply completed!"
echo ""
terraform output
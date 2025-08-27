#!/bin/bash
set -e

echo "🚀 Initializing Terraform for AI DevOps Platform..."
echo "===================================================="

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"

echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"

# Create terraform.tfvars file
cat > infrastructure/terraform/terraform.tfvars << EOF
aws_region     = "$AWS_REGION"
environment    = "dev"
aws_account_id = "$AWS_ACCOUNT_ID"
project_name   = "ai-devops-platform"
EOF

echo "✅ Created terraform.tfvars file"

# Initialize Terraform with backend configuration
cd infrastructure/terraform

# Check if S3 bucket for Terraform state already exists
if aws s3 ls "s3://ai-devops-platform-tfstate-$AWS_ACCOUNT_ID" --region $AWS_REGION 2>/dev/null; then
    echo "✅ S3 bucket for Terraform state already exists"
else
    echo "⚠️  S3 bucket for Terraform state doesn't exist. Please create it first:"
    echo "   aws s3 mb s3://ai-devops-platform-tfstate-$AWS_ACCOUNT_ID --region $AWS_REGION"
    echo "   aws s3api put-bucket-versioning --bucket ai-devops-platform-tfstate-$AWS_ACCOUNT_ID --versioning-configuration Status=Enabled"
    exit 1
fi

# Initialize Terraform
terraform init \
  -backend-config="bucket=ai-devops-platform-tfstate-$AWS_ACCOUNT_ID" \
  -backend-config="region=$AWS_REGION" \
  -backend-config="encrypt=true"

echo ""
echo "✅ Terraform initialized successfully!"
echo ""
echo "Next steps:"
echo "1. Run: terraform plan"
echo "2. Run: terraform apply"
echo ""
echo "If you get 'already exists' errors, run:"
echo "   terraform import aws_s3_bucket.tfstate ai-devops-platform-tfstate-$AWS_ACCOUNT_ID"
echo "   terraform import module.iam.aws_iam_policy.ai_devops_policy arn:aws:iam::$AWS_ACCOUNT_ID:policy/AIDevOpsPlatformPolicy"
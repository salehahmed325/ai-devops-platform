# scripts/terraform-init.sh
#!/bin/bash
set -e

echo "🚀 Initializing Terraform for AI DevOps Platform..."
echo "===================================================="

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-east-1"

echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"

# Create terraform.tfvars file in the terraform directory
cat > infrastructure/terraform/terraform.tfvars << EOF
aws_region     = "$AWS_REGION"
environment    = "dev"
aws_account_id = "$AWS_ACCOUNT_ID"
project_name   = "ai-devops-platform"
EOF

echo "✅ Created terraform.tfvars file"

# Initialize Terraform
cd infrastructure/terraform
terraform init

echo ""
echo "✅ Terraform initialized successfully!"
echo ""
echo "Next steps:"
echo "1. Run: terraform plan"
echo "2. Run: terraform apply"
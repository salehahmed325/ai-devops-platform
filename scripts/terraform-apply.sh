# scripts/terraform-apply.sh
#!/bin/bash
set -e

echo "🚀 Applying Terraform configuration..."
echo "======================================"

cd ../infrastructure/terraform

# Plan and apply
terraform plan -out=tfplan
terraform apply tfplan

# Output the results
echo ""
echo "✅ Terraform apply completed!"
echo ""
terraform output
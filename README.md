# ai-devops-platform
Cloud-native AI DevOps monitoring and optimization platform

## Infrastructure as Code

This project uses Terraform to manage AWS infrastructure:

```bash
# Initialize Terraform
./scripts/terraform-init.sh

# Plan changes
cd infrastructure/terraform
terraform plan

# Apply changes
terraform apply

# Destroy infrastructure (be careful!)
terraform destroy# Testing CI/CD Pipeline
# Testing CI/CD Pipeline
# Testing CI/CD Pipeline Again

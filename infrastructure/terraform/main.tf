# Get AWS account ID
data "aws_caller_identity" "current" {}

# Local values
locals {
  aws_account_id = data.aws_caller_identity.current.account_id
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# S3 Bucket for Terraform state (create this first manually)
resource "aws_s3_bucket" "tfstate" {
  bucket = "ai-devops-platform-tfstate-${local.aws_account_id}"

  tags = merge(local.common_tags, {
    Name = "Terraform State Bucket"
  })
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ECR Repositories
module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
  repositories = ["edge-agent", "central-brain"]
}

# S3 Bucket for AI Models
module "s3_models" {
  source = "./modules/s3"

  bucket_name = "ai-devops-platform-models-${local.aws_account_id}"
  environment = var.environment
  project_name = var.project_name
}

# IAM Roles
module "iam" {
  source = "./modules/iam"

  project_name    = var.project_name
  environment     = var.environment
  aws_account_id  = local.aws_account_id
  s3_model_bucket = module.s3_models.bucket_name
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "main" {
  name              = var.project_name
  retention_in_days = 30

  tags = local.common_tags
}
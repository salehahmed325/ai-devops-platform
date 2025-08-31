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
  tags         = local.common_tags
}

# S3 Bucket for AI Models
module "s3_models" {
  source = "./modules/s3"

  bucket_name  = "ai-devops-platform-models-${local.aws_account_id}"
  project_name = var.project_name
  environment  = var.environment
  tags         = local.common_tags
}

# IAM Roles
module "iam" {
  source = "./modules/iam"

  project_name    = var.project_name
  environment     = var.environment
  aws_account_id  = local.aws_account_id
  s3_model_bucket = module.s3_models.bucket_name
  tags            = local.common_tags
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "main" {
  name              = var.project_name
  retention_in_days = 30

    tags = local.common_tags
}

# --- Networking Data Sources ---

# Get the default VPC
data "aws_vpc" "default" {
  default = true
}

# Get all subnets in the default VPC
data "aws_subnets" "all" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}


# --- ECS Deployment ---

module "ecs" {
    source = "./modules/ecs"

    project_name                = var.project_name
    environment                 = var.environment
    aws_region                  = var.aws_region
    tags                        = local.common_tags

    vpc_id                      = data.aws_vpc.default.id
    public_subnet_ids           = data.aws_subnets.all.ids
    private_subnet_ids          = data.aws_subnets.all.ids

    # You will need to replace this with the actual image URI from ECR after the CI/CD pipeline runs
    container_image             = "680763994293.dkr.ecr.us-east-1.amazonaws.com/central-brain:latest" # placeholder
    ecs_task_execution_role_arn = module.iam.ecs_task_execution_role_arn
}

# --- VPC Endpoints for ECR ---

# ECR API Endpoint
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type = "Interface"
  private_dns_enabled = true
  subnet_ids        = data.aws_subnets.all.ids
  security_group_ids = [
    module.ecs.ecs_service_security_group_id
  ]
  tags = local.common_tags
}

# ECR Docker Registry Endpoint
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type = "Interface"
  private_dns_enabled = true
  subnet_ids        = data.aws_subnets.all.ids
  security_group_ids = [
    module.ecs.ecs_service_security_group_id
  ]
  tags = local.common_tags
}

# S3 Gateway Endpoint (for ECR image layers)
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = data.aws_vpc.default.id
  service_name = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  tags = local.common_tags
}
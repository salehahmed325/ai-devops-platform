# Get AWS account ID and define common tags
data "aws_caller_identity" "current" {}

locals {
  aws_account_id = data.aws_caller_identity.current.account_id
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# --- VPC --
# Using the official Terraform AWS VPC module
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.5.2"

  name = "${var.project_name}-vpc-${var.environment}"
  cidr = "10.0.0.0/16"

  azs             = data.aws_availability_zones.available.names
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
  enable_dns_hostnames = true

  tags = local.common_tags
}

data "aws_availability_zones" "available" {}


# --- IAM Roles ---
module "iam" {
  source          = "./modules/iam"
  project_name    = var.project_name
  environment     = var.environment
  aws_account_id  = local.aws_account_id
  s3_model_bucket     = module.s3_models.bucket_name
  dynamodb_table_name = "ai-devops-platform-data"
  dynamodb_table_arn       = module.dynamodb_data.table_arn # Pass the ARN for data table
  dynamodb_alert_table_arn = aws_dynamodb_table.alert_configs.arn # Pass the ARN for alert configs table
  tags                     = local.common_tags
}

# --- ECR Repositories ---
module "ecr" {
  source       = "./modules/ecr"
  project_name = var.project_name
  environment  = var.environment
  repositories = ["edge-agent", "central-brain"]
  tags         = local.common_tags
}

# --- S3 Bucket for AI Models ---
module "s3_models" {
  source       = "./modules/s3"
  project_name = var.project_name
  environment  = var.environment
  bucket_name  = "ai-devops-platform-models-${local.aws_account_id}"
  tags         = local.common_tags
}

# --- DynamoDB Table (for ingested data) ---
module "dynamodb_data" {
  source     = "./modules/dynamodb"
  table_name = "ai-devops-platform-data"
  tags       = local.common_tags
}

# --- DynamoDB Table (for alert configurations) ---
resource "aws_dynamodb_table" "alert_configs" {
  name         = "ai-devops-platform-alert-configs"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "cluster_id"

  attribute {
    name = "cluster_id"
    type = "S"
  }

  tags = local.common_tags
}


# --- ECS Deployment ---
module "ecs" {
  source = "./modules/ecs"

  project_name    = var.project_name
  environment     = var.environment
  aws_region      = var.aws_region
  tags            = local.common_tags

  vpc_id          = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnets
  private_subnet_ids  = module.vpc.private_subnets

  # Dynamically construct the container image URI
  container_image             = "${module.ecr.repository_urls["central-brain"]}:${var.container_image_tag}"
  ecs_task_execution_role_arn = module.iam.ecs_task_execution_role_arn
  telegram_bot_token          = var.telegram_bot_token # Pass Telegram bot token
}

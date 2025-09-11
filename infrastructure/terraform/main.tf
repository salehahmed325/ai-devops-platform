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
  dynamodb_logs_table_arn  = module.dynamodb_data.logs_table_arn # Pass the ARN for logs table
  tags                     = local.common_tags
}

# --- ECR Repositories ---
module "ecr" {
  source       = "./modules/ecr"
  project_name = var.project_name
  environment  = var.environment
  repositories = ["edge-agent", "fluent-bit"]
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

# --- S3 Bucket for Lambda Code ---
module "s3_lambda_code" {
  source       = "./modules/s3"
  project_name = var.project_name
  environment  = var.environment
  bucket_name  = "ai-devops-platform-lambda-code-${local.aws_account_id}"
  tags         = local.common_tags
}

# --- Lambda Deployment for Central Brain ---
module "lambda_central_brain" {
  source = "./modules/lambda"

  project_name = var.project_name
  environment  = var.environment
  tags         = local.common_tags

  function_name  = "${var.project_name}-central-brain-${var.environment}"
  iam_role_arn   = module.iam.lambda_execution_role_arn
  s3_bucket_name = module.s3_lambda_code.bucket_name
  s3_key         = var.lambda_zip_key
  
  
  lambda_environment_variables = {
    API_KEY                           = var.api_key
    TELEGRAM_BOT_TOKEN                = var.telegram_bot_token
    DYNAMODB_TABLE_NAME               = module.dynamodb_data.table_name
    DYNAMODB_LOGS_TABLE_NAME          = module.dynamodb_data.logs_table_name
    DYNAMODB_ALERT_CONFIGS_TABLE_NAME = aws_dynamodb_table.alert_configs.name
  }
}

# --- API Gateway for Central Brain Lambda ---
module "api_gateway_central_brain" {
  source = "./modules/api-gateway"

  project_name = var.project_name
  environment  = var.environment
  tags         = local.common_tags

  lambda_invoke_arn = module.lambda_central_brain.function_invoke_arn
  function_name     = module.lambda_central_brain.function_name
}
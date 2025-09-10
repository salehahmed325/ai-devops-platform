variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "ai-devops-platform"
}

variable "container_image_tag" {
  description = "The Docker image tag to deploy for the central-brain service"
  type        = string
  default     = "latest" # Default value, will be overridden by CI/CD
}

variable "telegram_bot_token" {
  description = "Telegram bot token for sending alerts"
  type        = string
  sensitive   = true
  default     = "" # Provide a default empty string
}

variable "api_key" {
  description = "The API key for securing the central-brain endpoint"
  type        = string
  sensitive   = true
}

variable "lambda_zip_key" {
  description = "The S3 key for the Lambda function deployment package (zip file)"
  type        = string
}
variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "s3_model_bucket" {
  description = "S3 bucket name for AI models"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table for data storage"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table for data storage"
  type        = string
}

variable "dynamodb_alert_table_arn" {
  description = "ARN of the DynamoDB table for alert configurations"
  type        = string
}

variable "dynamodb_logs_table_arn" {
  description = "ARN of the DynamoDB table for logs storage"
  type        = string
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}
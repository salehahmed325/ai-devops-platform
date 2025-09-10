variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "environment" {
  description = "The environment (e.g., dev, prod)"
  type        = string
}

variable "tags" {
  description = "A map of tags to assign to the resources"
  type        = map(string)
  default     = {}
}

variable "function_name" {
  description = "The name of the Lambda function"
  type        = string
}

variable "iam_role_arn" {
  description = "The ARN of the IAM role for the Lambda function"
  type        = string
}

variable "s3_bucket_name" {
  description = "The name of the S3 bucket containing the Lambda code"
  type        = string
}

variable "s3_key" {
  description = "The S3 key of the Lambda deployment package"
  type        = string
}

variable "handler" {
  description = "The Lambda function handler"
  type        = string
  default     = "main.handler"
}

variable "runtime" {
  description = "The Lambda function runtime"
  type        = string
  default     = "python3.9"
}

variable "timeout" {
  description = "The timeout for the Lambda function in seconds"
  type        = number
  default     = 30
}

variable "memory_size" {
  description = "The memory size for the Lambda function in MB"
  type        = number
  default     = 256
}

variable "lambda_environment_variables" {
  description = "A map of environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}

variable "lambda_layer_arn" {
  description = "The ARN of the Lambda Layer to attach to the function"
  type        = string
  default     = null # Make it optional
}

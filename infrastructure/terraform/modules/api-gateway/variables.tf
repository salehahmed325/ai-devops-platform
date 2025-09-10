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

variable "lambda_invoke_arn" {
  description = "The Invoke ARN of the Lambda function to integrate with"
  type        = string
}

variable "function_name" {
  description = "The name of the Lambda function"
  type        = string
}

variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "environment" {
  description = "The environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "The AWS region to deploy to"
  type        = string
}

variable "vpc_id" {
  description = "The ID of the VPC to deploy into"
  type        = string
}

variable "private_subnet_ids" {
  description = "A list of private subnet IDs for the ECS tasks"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "A list of public subnet IDs for the Load Balancer"
  type        = list(string)
}

variable "container_image" {
  description = "The Docker image for the container"
  type        = string
}

variable "container_port" {
  description = "The port the container listens on"
  type        = number
  default     = 8000
}

variable "cpu" {
  description = "The number of CPU units to reserve for the container"
  type        = number
  default     = 256
}

variable "memory" {
  description = "The amount of memory (in MiB) to reserve for the container"
  type        = number
  default     = 512
}

variable "ecs_task_execution_role_arn" {
  description = "The ARN of the ECS task execution role"
  type        = string
}

variable "telegram_bot_token" {
  description = "Telegram bot token for sending alerts"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "A map of tags to assign to the resources"
  type        = map(string)
  default     = {}
}

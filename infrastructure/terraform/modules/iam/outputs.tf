output "ecs_task_execution_role_arn" {
  description = "The ARN of the IAM role for ECS Task Execution"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

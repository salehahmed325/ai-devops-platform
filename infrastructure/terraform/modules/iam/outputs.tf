output "ecs_task_execution_role_arn" {
  description = "The ARN of the IAM role for ECS Task Execution"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "lambda_execution_role_arn" {
  description = "The ARN of the IAM role for Lambda Function Execution"
  value       = aws_iam_role.lambda_execution_role.arn
}

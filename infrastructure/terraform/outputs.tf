output "ecr_repositories" {
  description = "Map of ECR repository URLs"
  value       = module.ecr.repository_urls
}

output "s3_model_bucket" {
  description = "S3 bucket for AI models"
  value       = module.s3_models.bucket_name
}

output "iam_roles" {
  description = "IAM roles created"
  value       = module.iam.role_arns
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.main.name
}

output "central_brain_url" {
  description = "The public URL of the Central Brain service"
  value       = "http://${module.ecs.load_balancer_dns_name}"
}

resource "aws_ecr_repository" "this" {
  for_each = toset(var.repositories)

  name = each.key
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.tags, {
    Name = each.key
  })
}

output "repository_urls" {
  description = "Map of ECR repository URLs"
  value       = { for k, v in aws_ecr_repository.this : k => v.repository_url }
}
# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "ecsTaskExecutionRole"
  })
}

# Attach the standard Amazon ECS Task Execution Role Policy
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Custom policy for AI DevOps Platform
resource "aws_iam_policy" "ai_devops_policy" {
  name        = "AIDevOpsPlatformPolicy"
  description = "Policy for AI DevOps Platform resources"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRAccess"
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:GetAuthorizationToken",
          "ecr:DescribeRepositories"
        ]
        Resource = "*"
      },
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_model_bucket}",
          "arn:aws:s3:::${var.s3_model_bucket}/*"
        ]
      },
      {
        Sid    = "CloudWatchAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "arn:aws:logs:*:*:log-group:${var.project_name}*"
      }
    ]
  })

  tags = var.tags

  lifecycle {
    ignore_changes = [
      # Ignore changes to the policy document since it's managed externally
      policy
    ]
  }

}

# Attach custom policy to ECS role
resource "aws_iam_role_policy_attachment" "ai_devops_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ai_devops_policy.arn
}

output "role_arns" {
  description = "IAM role ARNs"
  value = {
    ecs_task_execution_role = aws_iam_role.ecs_task_execution_role.arn
  }
}
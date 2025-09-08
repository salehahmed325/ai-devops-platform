resource "aws_dynamodb_table" "main" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST" # Use on-demand capacity

  hash_key  = "cluster_id"
  range_key = "metric_identifier"

  attribute {
    name = "cluster_id"
    type = "S" # String
  }

  attribute {
    name = "metric_identifier"
    type = "S" # String
  }

  # Attributes for GSI
  attribute {
    name = "metric_name"
    type = "S"
  }

  attribute {
    name = "instance_job_composite"
    type = "S"
  }

  global_secondary_index {
    name               = "MetricName-InstanceJob-index"
    hash_key           = "metric_name"
    range_key          = "instance_job_composite"
    projection_type    = "ALL"
    read_capacity      = 1
    write_capacity     = 1
  }

  tags = var.tags
}

resource "aws_dynamodb_table" "logs" {
  name         = "ai-devops-platform-logs"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "cluster_id"
  range_key = "timestamp"

  attribute {
    name = "cluster_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  tags = var.tags
}

output "table_name" {
  description = "The name of the DynamoDB table"
  value       = aws_dynamodb_table.main.name
}

output "table_arn" {
  description = "The ARN of the DynamoDB table"
  value       = aws_dynamodb_table.main.arn
}

output "logs_table_name" {
  description = "The name of the DynamoDB logs table"
  value       = aws_dynamodb_table.logs.name
}

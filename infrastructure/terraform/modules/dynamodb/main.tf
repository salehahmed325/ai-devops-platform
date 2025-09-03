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
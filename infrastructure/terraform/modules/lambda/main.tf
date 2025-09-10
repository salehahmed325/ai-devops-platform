resource "aws_lambda_function" "this" {
  function_name = var.function_name
  role          = var.iam_role_arn

  s3_bucket = var.s3_bucket_name
  s3_key    = var.s3_key

  handler = var.handler
  runtime = var.runtime
  timeout = var.timeout
  memory_size = var.memory_size

  environment {
    variables = var.lambda_environment_variables
  }

  tags = var.tags

  # Attach Lambda Layer if provided
  layers = var.lambda_layer_arn == null ? [] : [var.lambda_layer_arn]
}

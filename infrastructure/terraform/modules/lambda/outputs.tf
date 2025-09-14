output "function_url" {
  description = "The URL of the Lambda function"
  value       = aws_lambda_function_url.this.function_url
}

output "function_invoke_arn" {
    description = "The ARN to be used in other resources to invoke this function"
    value = aws_lambda_function.this.invoke_arn
}

output "function_name" {
    description = "The name of the lambda function"
    value = aws_lambda_function.this.function_name
}
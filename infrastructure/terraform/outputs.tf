output "lambda_function_url" {
  description = "The URL of the Central Brain Lambda function"
  value       = module.lambda_central_brain.function_url
}
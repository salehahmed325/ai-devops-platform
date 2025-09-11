output "central_brain_api_endpoint" {
  description = "The invoke URL for the Central Brain API Gateway"
  value       = module.api_gateway_central_brain.api_endpoint
}


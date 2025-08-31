output "load_balancer_dns_name" {
  description = "The DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "ecs_cluster_name" {
  description = "The name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "The name of the ECS service"
  value       = aws_ecs_service.main.name
}

output "ecs_service_security_group_id" {
  description = "The ID of the security group attached to the ECS service"
  value       = aws_security_group.ecs_service.id
}


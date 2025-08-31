data "aws_availability_zones" "available" {}

# --- VPC ---
# Using the official Terraform AWS VPC module
# https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws/latest
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.5.2"

  name = "${var.project_name}-vpc-${var.environment}"
  cidr = "10.0.0.0/16"

  azs             = data.aws_availability_zones.available.names
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
  enable_dns_hostnames = true

  tags = local.common_tags
}


# --- ECS Deployment ---

module "ecs" {
  source = "./modules/ecs"

  project_name    = var.project_name
  environment     = var.environment
  aws_region      = var.aws_region
  tags            = local.common_tags

  vpc_id          = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnets
  private_subnet_ids  = module.vpc.private_subnets

  container_image = "680763994293.dkr.ecr.us-east-1.amazonaws.com/central-brain:latest" # placeholder
  ecs_task_execution_role_arn = module.iam.ecs_task_execution_role_arn
}

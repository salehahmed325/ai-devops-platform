terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # This will be configured later after the S3 bucket is created
    bucket = "ai-devops-platform-tfstate-${var.aws_account_id}"
    key    = "terraform.tfstate"
    region = var.aws_region
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ai-devops-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
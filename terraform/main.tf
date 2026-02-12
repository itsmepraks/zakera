terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket         = "zakera-terraform-state"
    key            = "zakera/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "zakera-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "Zakera"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"
  
  environment         = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  
  tags = var.tags
}

# ECS Cluster
module "ecs" {
  source = "./modules/ecs"
  
  environment             = var.environment
  vpc_id                 = module.vpc.vpc_id
  private_subnet_ids     = module.vpc.private_subnet_ids
  alb_security_group_id  = module.alb.security_group_id
  
  app_image              = var.app_image
  app_port               = var.app_port
  app_count              = var.app_count
  
  cpu                    = var.fargate_cpu
  memory                 = var.fargate_memory
  
  database_url           = module.rds.database_url
  redis_url              = module.elasticache.redis_url
  
  openai_api_key         = var.openai_api_key
  anthropic_api_key      = var.anthropic_api_key
  google_api_key         = var.google_api_key
  secret_key             = var.secret_key
  
  tags = var.tags
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"
  
  environment        = var.environment
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  
  certificate_arn = var.certificate_arn
  domain_name     = var.domain_name
  
  tags = var.tags
}

# RDS PostgreSQL Database
module "rds" {
  source = "./modules/rds"
  
  environment          = var.environment
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  
  db_name             = var.db_name
  db_username         = var.db_username
  db_password         = var.db_password
  
  instance_class      = var.db_instance_class
  allocated_storage   = var.db_allocated_storage
  
  backup_retention_period = var.db_backup_retention_period
  
  tags = var.tags
}

# ElastiCache Redis
module "elasticache" {
  source = "./modules/elasticache"
  
  environment        = var.environment
  vpc_id            = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  
  node_type         = var.redis_node_type
  num_cache_nodes   = var.redis_num_nodes
  
  tags = var.tags
}

# S3 Bucket for Assets
module "s3" {
  source = "./modules/s3"
  
  environment = var.environment
  bucket_name = "${var.environment}-zakera-assets"
  
  tags = var.tags
}

# CloudWatch Monitoring
module "monitoring" {
  source = "./modules/monitoring"
  
  environment = var.environment
  
  ecs_cluster_name = module.ecs.cluster_name
  ecs_service_name = module.ecs.service_name
  
  alb_arn_suffix = module.alb.alb_arn_suffix
  
  db_instance_identifier = module.rds.db_instance_identifier
  
  tags = var.tags
}

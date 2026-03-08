# Terraform configuration for AWS EKS deployment
# Provisions production-ready Kubernetes cluster for Zakera

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
  
  backend "s3" {
    bucket         = "zakera-terraform-state"
    key            = "production/terraform.tfstate"
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
      Owner       = "Platform Team"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local variables
locals {
  cluster_name = "zakera-${var.environment}"
  
  common_tags = {
    Project     = "Zakera"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# VPC for EKS cluster
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  
  name = "${local.cluster_name}-vpc"
  cidr = var.vpc_cidr
  
  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs
  
  enable_nat_gateway   = true
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  # Enable VPC Flow Logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_iam_role  = true
  create_flow_log_cloudwatch_log_group = true
  
  # Tags for EKS
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }
  
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }
  
  tags = local.common_tags
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"
  
  cluster_name    = local.cluster_name
  cluster_version = "1.28"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  # Cluster endpoint access
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true
  
  # Enable IRSA (IAM Roles for Service Accounts)
  enable_irsa = true
  
  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }
  
  # Managed node groups
  eks_managed_node_groups = {
    # General purpose nodes
    general = {
      name           = "${local.cluster_name}-general"
      instance_types = ["t3.xlarge"]
      
      min_size     = 3
      max_size     = 10
      desired_size = 3
      
      disk_size = 50
      
      labels = {
        role = "general"
      }
      
      tags = {
        NodeGroup = "general"
      }
    }
    
    # Compute optimized for AI workloads
    compute = {
      name           = "${local.cluster_name}-compute"
      instance_types = ["c5.2xlarge"]
      
      min_size     = 2
      max_size     = 20
      desired_size = 3
      
      disk_size = 100
      
      labels = {
        role = "compute"
        "node-role.kubernetes.io/compute" = "true"
      }
      
      taints = [{
        key    = "node-role.kubernetes.io/compute"
        value  = "true"
        effect = "NoSchedule"
      }]
      
      tags = {
        NodeGroup = "compute"
      }
    }
  }
  
  # Cluster security group rules
  cluster_security_group_additional_rules = {
    ingress_nodes_ephemeral_ports_tcp = {
      description                = "Nodes on ephemeral ports"
      protocol                   = "tcp"
      from_port                  = 1025
      to_port                    = 65535
      type                       = "ingress"
      source_node_security_group = true
    }
  }
  
  # Node security group rules
  node_security_group_additional_rules = {
    ingress_self_all = {
      description = "Node to node all ports/protocols"
      protocol    = "-1"
      from_port   = 0
      to_port     = 0
      type        = "ingress"
      self        = true
    }
  }
  
  tags = local.common_tags
}

# RDS for PostgreSQL
resource "aws_db_instance" "postgres" {
  identifier = "${local.cluster_name}-postgres"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.db_instance_class
  
  allocated_storage     = 100
  max_allocated_storage = 500
  storage_type          = "gp3"
  storage_encrypted     = true
  
  db_name  = "zakera_prod"
  username = "zakera_admin"
  password = var.db_password
  port     = 5432
  
  vpc_security_group_ids = [aws_security_group.postgres_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "${local.cluster_name}-postgres-final-snapshot"
  
  performance_insights_enabled = true
  
  tags = merge(local.common_tags, {
    Name = "${local.cluster_name}-postgres"
  })
}

# ElastiCache for Redis
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${local.cluster_name}-redis"
  replication_group_description = "Redis cluster for Zakera caching"
  
  engine         = "redis"
  engine_version = "7.0"
  node_type      = var.redis_node_type
  
  num_cache_clusters         = 3
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  port = 6379
  
  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis_sg.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.redis_auth_token
  
  snapshot_retention_limit = 7
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:07:00"
  
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }
  
  tags = local.common_tags
}

# Security Groups
resource "aws_security_group" "postgres_sg" {
  name        = "${local.cluster_name}-postgres-sg"
  description = "Security group for PostgreSQL"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
    description = "PostgreSQL from EKS"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound"
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.cluster_name}-postgres-sg"
  })
}

resource "aws_security_group" "redis_sg" {
  name        = "${local.cluster_name}-redis-sg"
  description = "Security group for Redis"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
    description = "Redis from EKS"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound"
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.cluster_name}-redis-sg"
  })
}

# Subnet groups
resource "aws_db_subnet_group" "postgres" {
  name       = "${local.cluster_name}-postgres-subnet"
  subnet_ids = module.vpc.private_subnets
  
  tags = merge(local.common_tags, {
    Name = "${local.cluster_name}-postgres-subnet"
  })
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.cluster_name}-redis-subnet"
  subnet_ids = module.vpc.private_subnets
  
  tags = local.common_tags
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "redis" {
  name              = "/aws/elasticache/${local.cluster_name}-redis"
  retention_in_days = 30
  
  tags = local.common_tags
}

# Outputs
output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_id
}

output "postgres_endpoint" {
  description = "PostgreSQL endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive   = true
}

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_id}"
}

# VPC Configuration

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  
  name = "${var.project_name}-${var.environment}-vpc"
  cidr = var.vpc_cidr
  
  azs             = var.availability_zones
  private_subnets = [for k, v in var.availability_zones : cidrsubnet(var.vpc_cidr, 4, k)]
  public_subnets  = [for k, v in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, k + 100)]
  database_subnets = [for k, v in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, k + 200)]
  
  enable_nat_gateway   = true
  single_nat_gateway   = false  # HA: one NAT per AZ
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  # VPC Flow Logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_iam_role  = true
  create_flow_log_cloudwatch_log_group = true
  
  # Tags
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
    Type                     = "public"
  }
  
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    Type                              = "private"
  }
  
  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-${var.environment}-vpc"
    }
  )
}

# Security Groups
resource "aws_security_group" "eks_cluster" {
  name_prefix = "${var.project_name}-eks-cluster-"
  description = "Security group for EKS cluster"
  vpc_id      = module.vpc.vpc_id
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-eks-cluster-sg"
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-rds-"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_cluster.id]
    description     = "PostgreSQL from EKS"
  }
  
  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-redis-"
  description = "Security group for ElastiCache Redis"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_cluster.id]
    description     = "Redis from EKS"
  }
  
  tags = {
    Name = "${var.project_name}-redis-sg"
  }
}

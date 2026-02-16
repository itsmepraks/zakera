# Terraform Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "zakera"
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

# EKS Configuration
variable "cluster_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "node_instance_types" {
  description = "EC2 instance types for nodes"
  type        = list(string)
  default     = ["t3.medium", "t3.large"]
}

variable "node_desired_size" {
  description = "Desired number of nodes"
  type        = number
  default     = 3
}

variable "node_min_size" {
  description = "Minimum number of nodes"
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum number of nodes"
  type        = number
  default     = 10
}

# Database Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 100
}

variable "db_backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  default     = 7
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 1
}

# Domain Configuration
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "zakera.io"
}

variable "certificate_arn" {
  description = "ACM certificate ARN for SSL"
  type        = string
  default     = ""
}

# Monitoring
variable "enable_cloudwatch" {
  description = "Enable CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# Tags
variable "additional_tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}

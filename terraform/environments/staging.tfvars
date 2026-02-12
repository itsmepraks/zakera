# Staging Environment Configuration

environment = "staging"
aws_region  = "us-east-1"

# Networking
vpc_cidr           = "10.1.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]

# Application
app_port  = 8000
app_count = 2

# ECS Fargate
fargate_cpu    = 1024
fargate_memory = 2048

# Database
db_name                    = "zakera_staging"
db_instance_class          = "db.t3.medium"
db_allocated_storage       = 50
db_backup_retention_period = 7

# Redis
redis_node_type  = "cache.t3.medium"
redis_num_nodes  = 1

# Tags
tags = {
  Project     = "Zakera"
  Environment = "Staging"
  ManagedBy   = "Terraform"
  Team        = "Engineering"
}

# Production Environment Configuration

environment = "production"
aws_region  = "us-east-1"

# Networking
vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# Application
app_port  = 8000
app_count = 3

# ECS Fargate
fargate_cpu    = 2048
fargate_memory = 4096

# Database
db_name                    = "zakera_prod"
db_instance_class          = "db.r5.large"
db_allocated_storage       = 200
db_backup_retention_period = 14

# Redis
redis_node_type  = "cache.r5.large"
redis_num_nodes  = 3

# Tags
tags = {
  Project     = "Zakera"
  Environment = "Production"
  ManagedBy   = "Terraform"
  Team        = "Engineering"
}

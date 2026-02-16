# ElastiCache Redis Configuration

resource "aws_elasticache_subnet_group" "zakera" {
  name       = "${var.project_name}-${var.environment}-redis-subnet"
  subnet_ids = module.vpc.private_subnets
  
  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

resource "aws_elasticache_parameter_group" "zakera" {
  name   = "${var.project_name}-${var.environment}-redis7"
  family = "redis7"
  
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
  
  parameter {
    name  = "timeout"
    value = "300"
  }
  
  tags = {
    Name = "${var.project_name}-redis-params"
  }
}

resource "aws_elasticache_cluster" "zakera" {
  cluster_id           = "${var.project_name}-${var.environment}"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.redis_node_type
  num_cache_nodes      = var.redis_num_cache_nodes
  parameter_group_name = aws_elasticache_parameter_group.zakera.name
  subnet_group_name    = aws_elasticache_subnet_group.zakera.name
  security_group_ids   = [aws_security_group.redis.id]
  
  # Snapshots
  snapshot_retention_limit = 5
  snapshot_window         = "03:00-04:00"
  
  # Maintenance
  maintenance_window = "sun:05:00-sun:06:00"
  
  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth.result
  
  # Notifications
  notification_topic_arn = aws_sns_topic.zakera_alerts.arn
  
  tags = {
    Name = "${var.project_name}-${var.environment}-redis"
  }
}

resource "random_password" "redis_auth" {
  length  = 32
  special = false
}

# Store Redis credentials
resource "aws_secretsmanager_secret" "redis_credentials" {
  name                    = "${var.project_name}/${var.environment}/redis"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "redis_credentials" {
  secret_id = aws_secretsmanager_secret.redis_credentials.id
  secret_string = jsonencode({
    endpoint   = aws_elasticache_cluster.zakera.cache_nodes[0].address
    port       = aws_elasticache_cluster.zakera.cache_nodes[0].port
    auth_token = random_password.redis_auth.result
    url        = "redis://:${random_password.redis_auth.result}@${aws_elasticache_cluster.zakera.cache_nodes[0].address}:${aws_elasticache_cluster.zakera.cache_nodes[0].port}/0"
  })
}

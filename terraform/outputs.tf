# Terraform Outputs

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "cluster_certificate_authority_data" {
  description = "EKS cluster certificate authority data"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "database_endpoint" {
  description = "RDS database endpoint"
  value       = aws_db_instance.zakera.endpoint
  sensitive   = true
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.zakera.db_name
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_cluster.zakera.cache_nodes[0].address
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_cluster.zakera.cache_nodes[0].port
}

output "s3_data_bucket" {
  description = "S3 data bucket name"
  value       = aws_s3_bucket.zakera_data.id
}

output "s3_backup_bucket" {
  description = "S3 backup bucket name"
  value       = aws_s3_bucket.zakera_backups.id
}

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.zakera_alerts.arn
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

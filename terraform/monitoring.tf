# CloudWatch and Monitoring Configuration

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "zakera_app" {
  name              = "/aws/eks/${var.project_name}-${var.environment}/app"
  retention_in_days = var.log_retention_days
  
  tags = {
    Name = "${var.project_name}-app-logs"
  }
}

resource "aws_cloudwatch_log_group" "zakera_access" {
  name              = "/aws/eks/${var.project_name}-${var.environment}/access"
  retention_in_days = var.log_retention_days
  
  tags = {
    Name = "${var.project_name}-access-logs"
  }
}

# SNS Topic for Alerts
resource "aws_sns_topic" "zakera_alerts" {
  name = "${var.project_name}-${var.environment}-alerts"
  
  tags = {
    Name = "${var.project_name}-alerts"
  }
}

resource "aws_sns_topic_subscription" "zakera_alerts_email" {
  topic_arn = aws_sns_topic.zakera_alerts.arn
  protocol  = "email"
  endpoint  = "alerts@zakera.io"  # Change this
}

# CloudWatch Alarms - API
resource "aws_cloudwatch_metric_alarm" "api_high_error_rate" {
  alarm_name          = "${var.project_name}-${var.environment}-api-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "5XXError"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "5"
  alarm_description   = "API error rate is too high"
  alarm_actions       = [aws_sns_topic.zakera_alerts.arn]
  
  dimensions = {
    LoadBalancer = module.eks.cluster_name
  }
}

resource "aws_cloudwatch_metric_alarm" "api_high_latency" {
  alarm_name          = "${var.project_name}-${var.environment}-api-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "2"
  alarm_description   = "API response time is too high"
  alarm_actions       = [aws_sns_topic.zakera_alerts.arn]
}

# CloudWatch Alarms - Database
resource "aws_cloudwatch_metric_alarm" "db_cpu_high" {
  alarm_name          = "${var.project_name}-${var.environment}-db-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "Database CPU utilization is high"
  alarm_actions       = [aws_sns_topic.zakera_alerts.arn]
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.zakera.id
  }
}

resource "aws_cloudwatch_metric_alarm" "db_storage_low" {
  alarm_name          = "${var.project_name}-${var.environment}-db-storage-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "10737418240"  # 10GB
  alarm_description   = "Database free storage is low"
  alarm_actions       = [aws_sns_topic.zakera_alerts.arn]
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.zakera.id
  }
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "zakera" {
  dashboard_name = "${var.project_name}-${var.environment}"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", { stat = "Average" }],
            [".", "DatabaseConnections", { stat = "Sum" }],
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Database Metrics"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", { stat = "Average" }],
            [".", "NetworkBytesIn", { stat = "Sum" }],
            [".", "NetworkBytesOut", { stat = "Sum" }],
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Redis Metrics"
        }
      }
    ]
  })
}

# Zakera Deployment Guide

## AWS Deployment with Terraform

This guide covers deploying Zakera to AWS using Terraform for infrastructure as code.

## Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.0 installed
- AWS CLI configured with credentials
- Docker for building application images
- Domain name (optional, for custom domain)

## Architecture Overview

The deployment creates the following infrastructure:

- **VPC**: Custom VPC with public and private subnets across multiple AZs
- **ECS Fargate**: Containerized application deployment with auto-scaling
- **Application Load Balancer**: HTTPS load balancer with SSL/TLS termination
- **RDS PostgreSQL**: Managed database with automated backups and multi-AZ
- **ElastiCache Redis**: In-memory cache for sessions and rate limiting
- **S3**: Object storage for assets and backups
- **CloudWatch**: Logging and monitoring with alerts
- **IAM**: Security roles and policies with least privilege

## Quick Start

### 1. Prepare Infrastructure State Backend

First, create an S3 bucket and DynamoDB table for Terraform state:

```bash
# Create S3 bucket for state
aws s3api create-bucket \
  --bucket zakera-terraform-state \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket zakera-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket zakera-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name zakera-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 2. Build and Push Docker Image

```bash
# Build the application image
docker build -t zakera:latest .

# Tag for ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker tag zakera:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/zakera:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/zakera:latest
```

### 3. Configure Environment Variables

Create a `terraform/terraform.tfvars` file:

```hcl
app_image = "<account-id>.dkr.ecr.us-east-1.amazonaws.com/zakera:latest"

# Domain and SSL
certificate_arn = "arn:aws:acm:us-east-1:<account-id>:certificate/<cert-id>"
domain_name     = "zakera.example.com"

# Database credentials
db_username = "zakera_admin"
db_password = "<strong-password>"

# API Keys
openai_api_key    = "sk-..."
anthropic_api_key = "sk-ant-..."
google_api_key    = "AIza..."

# Application secrets
secret_key = "<random-secret-key>"
```

**Security Note**: Never commit `terraform.tfvars` to version control. Use AWS Secrets Manager or environment variables for sensitive data in production.

### 4. Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Review the plan
terraform plan -var-file="environments/production.tfvars"

# Apply the configuration
terraform apply -var-file="environments/production.tfvars"
```

### 5. Configure DNS

After deployment, configure your domain's DNS:

```bash
# Get ALB DNS name
terraform output alb_dns_name

# Create Route53 record or update your DNS provider
aws route53 change-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "zakera.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "'$(terraform output -raw alb_zone_id)'",
          "DNSName": "'$(terraform output -raw alb_dns_name)'",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

## Environment-Specific Deployments

### Production

```bash
terraform apply -var-file="environments/production.tfvars"
```

### Staging

```bash
terraform apply -var-file="environments/staging.tfvars"
```

## Monitoring and Logging

### CloudWatch Logs

```bash
# View application logs
aws logs tail /aws/ecs/zakera-production --follow

# Search logs
aws logs filter-log-events \
  --log-group-name /aws/ecs/zakera-production \
  --filter-pattern "ERROR"
```

### Metrics Dashboard

Access CloudWatch dashboard:
- ECS service metrics (CPU, memory, request count)
- ALB metrics (request count, latency, errors)
- RDS metrics (connections, CPU, storage)
- Redis metrics (cache hits, evictions)

## Scaling

### Manual Scaling

```bash
# Update desired count in variables
terraform apply -var="app_count=5"
```

### Auto-scaling

Auto-scaling is configured based on:
- CPU utilization > 70%
- Memory utilization > 80%
- Request count per target

## Database Management

### Backups

Automated backups are configured with:
- Daily automated snapshots
- 7-day retention (staging) / 14-day retention (production)
- Point-in-time recovery enabled

### Migrations

```bash
# Connect to RDS via bastion or ECS task
aws ecs execute-command \
  --cluster zakera-production \
  --task <task-id> \
  --container app \
  --interactive \
  --command "/bin/bash"

# Run migrations
alembic upgrade head
```

## Security Best Practices

1. **Secrets Management**: Use AWS Secrets Manager for sensitive data
2. **IAM Roles**: Follow least privilege principle
3. **Network Security**: Resources in private subnets, ALB in public
4. **Encryption**: Enable at-rest and in-transit encryption
5. **SSL/TLS**: Use ACM certificates for HTTPS
6. **Regular Updates**: Keep dependencies and base images updated

## Cost Optimization

- Use Reserved Instances for predictable workloads
- Configure auto-scaling to match traffic patterns
- Use Fargate Spot for non-critical tasks
- Enable S3 lifecycle policies for old backups
- Monitor and right-size RDS instances

## Troubleshooting

### Service Not Starting

```bash
# Check ECS task logs
aws ecs describe-tasks --cluster zakera-production --tasks <task-id>

# View CloudWatch logs
aws logs tail /aws/ecs/zakera-production --follow
```

### High Latency

1. Check ALB target health
2. Review CloudWatch metrics
3. Check database connection pool
4. Verify Redis cache hit rate

### Database Connection Issues

1. Verify security group rules
2. Check RDS instance status
3. Review connection string
4. Monitor max connections

## Disaster Recovery

### Backup Strategy

- **Database**: Automated daily snapshots, 14-day retention
- **Configuration**: Terraform state in S3 with versioning
- **Application**: Docker images tagged and stored in ECR

### Recovery Procedure

1. Restore RDS from snapshot
2. Deploy infrastructure with Terraform
3. Deploy application from ECR image
4. Update DNS records
5. Verify functionality

Estimated RTO: < 1 hour
Estimated RPO: < 5 minutes

## Cleanup

To destroy all infrastructure:

```bash
terraform destroy -var-file="environments/production.tfvars"
```

**Warning**: This will delete all resources including databases and backups.

## Support

For deployment issues:
- Check CloudWatch logs
- Review Terraform outputs
- Consult AWS documentation
- Open an issue on GitHub

## Next Steps

- Set up CI/CD pipeline
- Configure custom domain
- Enable CloudFront CDN
- Set up monitoring alerts
- Implement blue-green deployments

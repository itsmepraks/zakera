# Terraform Infrastructure

> [!WARNING]
> **Legacy and unsupported.** This infrastructure has not been validated, conflicts with historical delivery assumptions, and is outside the Zakera vNext core project.

Terraform configuration for deploying Zakera to AWS.

## Architecture

Deploys:
- VPC with public/private subnets (multi-AZ)
- EKS cluster with managed node groups
- RDS PostgreSQL (multi-AZ)
- ElastiCache Redis
- S3 buckets (data, backups, logs)
- CloudWatch monitoring and alarms
- SNS for alerting

## Prerequisites

```bash
# Install Terraform
brew install terraform  # macOS
# or download from terraform.io

# Configure AWS
aws configure
```

## Usage

### Initialize

```bash
# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Format files
terraform fmt -recursive
```

### Plan

```bash
# Review changes
terraform plan

# Save plan
terraform plan -out=tfplan
```

### Apply

```bash
# Apply changes
terraform apply tfplan

# Or apply directly (with approval)
terraform apply
```

### Destroy

```bash
# Destroy all infrastructure (CAREFUL!)
terraform destroy
```

## Configuration

### Variables

Create `terraform.tfvars`:

```hcl
aws_region = "us-east-1"
environment = "production"
project_name = "zakera"

# Network
vpc_cidr = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# EKS
cluster_version = "1.28"
node_instance_types = ["t3.medium"]
node_desired_size = 3
node_min_size = 2
node_max_size = 10

# Database
db_instance_class = "db.t3.medium"
db_allocated_storage = 100

# Redis
redis_node_type = "cache.t3.micro"

# Domain
domain_name = "zakera.io"
```

## Outputs

After apply, get outputs:

```bash
# View all outputs
terraform output

# Specific output
terraform output cluster_name
terraform output database_endpoint

# Configure kubectl
aws eks update-kubeconfig \
  --name $(terraform output -raw cluster_name) \
  --region us-east-1
```

## State Management

### Remote State (S3)

State is stored in S3 with DynamoDB locking:

```bash
# Create state bucket (one-time)
aws s3 mb s3://zakera-terraform-state

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket zakera-terraform-state \
  --versioning-configuration Status=Enabled

# Create lock table
aws dynamodb create-table \
  --table-name zakera-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

## Modules

### VPC Module
- Public subnets (3 AZs)
- Private subnets (3 AZs)
- Database subnets (3 AZs)
- NAT gateways (HA)
- VPC Flow Logs

### EKS Module
- Managed control plane
- Managed node groups (on-demand + spot)
- Cluster addons (CoreDNS, kube-proxy, VPC-CNI)
- OIDC provider for IRSA

### RDS Module
- PostgreSQL 15
- Multi-AZ deployment
- Automated backups
- Performance Insights
- Enhanced monitoring

## Cost Estimates

| Resource | Monthly Cost |
|----------|-------------|
| EKS Cluster | $73 |
| EC2 Nodes (3x t3.medium) | $100 |
| RDS (db.t3.medium, multi-AZ) | $120 |
| ElastiCache (cache.t3.micro) | $15 |
| ALB | $20 |
| S3 + Data Transfer | $15 |
| **Total** | **~$343/month** |

## Best Practices

1. **Use remote state** (S3 + DynamoDB)
2. **Enable state locking**
3. **Use workspaces** for environments
4. **Tag all resources**
5. **Enable deletion protection**
6. **Review plans before apply**
7. **Keep Terraform version pinned**
8. **Use modules for reusability**

## Environments

```bash
# Create workspaces
terraform workspace new staging
terraform workspace new production

# Switch workspace
terraform workspace select production

# List workspaces
terraform workspace list
```

## Maintenance

### Update Infrastructure

```bash
# Pull latest changes
git pull

# Plan update
terraform plan

# Apply update
terraform apply
```

### Upgrade Kubernetes

```bash
# Update cluster version in variables.tf
cluster_version = "1.29"

# Apply
terraform apply
```

## Troubleshooting

### State Lock Issues

```bash
# Force unlock (if stuck)
terraform force-unlock LOCK_ID
```

### Resource Issues

```bash
# Import existing resource
terraform import aws_instance.example i-1234567890abcdef0

# Taint resource (force recreate)
terraform taint aws_instance.example
```

## Support

See main deployment guide: `docs/DEPLOYMENT.md`

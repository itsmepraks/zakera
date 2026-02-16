# EKS Cluster Configuration

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"
  
  cluster_name    = "${var.project_name}-${var.environment}"
  cluster_version = var.cluster_version
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  # Cluster endpoint configuration
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true
  
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
  
  # Node groups
  eks_managed_node_groups = {
    # General purpose nodes
    general = {
      name            = "${var.project_name}-general"
      instance_types  = var.node_instance_types
      capacity_type   = "ON_DEMAND"
      
      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size
      
      labels = {
        workload = "general"
      }
      
      taints = []
      
      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = 50
            volume_type           = "gp3"
            iops                  = 3000
            throughput            = 125
            encrypted             = true
            delete_on_termination = true
          }
        }
      }
      
      metadata_options = {
        http_endpoint               = "enabled"
        http_tokens                 = "required"
        http_put_response_hop_limit = 1
      }
    }
    
    # Spot instances for cost savings
    spot = {
      name           = "${var.project_name}-spot"
      instance_types = var.node_instance_types
      capacity_type  = "SPOT"
      
      min_size     = 0
      max_size     = 5
      desired_size = 1
      
      labels = {
        workload = "spot"
      }
      
      taints = [{
        key    = "spot"
        value  = "true"
        effect = "NoSchedule"
      }]
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
    
    ingress_cluster_all = {
      description                   = "Cluster to node all ports/protocols"
      protocol                      = "-1"
      from_port                     = 0
      to_port                       = 0
      type                          = "ingress"
      source_cluster_security_group = true
    }
  }
  
  tags = var.additional_tags
}

# OIDC provider for IRSA (IAM Roles for Service Accounts)
data "tls_certificate" "eks" {
  url = module.eks.cluster_oidc_issuer_url
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = module.eks.cluster_oidc_issuer_url
  
  tags = {
    Name = "${var.project_name}-eks-oidc"
  }
}

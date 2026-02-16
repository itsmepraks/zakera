# S3 Buckets for Storage

# Application data bucket
resource "aws_s3_bucket" "zakera_data" {
  bucket = "${var.project_name}-${var.environment}-data-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "${var.project_name}-data"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "zakera_data" {
  bucket = aws_s3_bucket.zakera_data.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "zakera_data" {
  bucket = aws_s3_bucket.zakera_data.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "zakera_data" {
  bucket = aws_s3_bucket.zakera_data.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "zakera_data" {
  bucket = aws_s3_bucket.zakera_data.id
  
  rule {
    id     = "archive-old-data"
    status = "Enabled"
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    expiration {
      days = 365
    }
  }
}

# Backup bucket
resource "aws_s3_bucket" "zakera_backups" {
  bucket = "${var.project_name}-${var.environment}-backups-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "${var.project_name}-backups"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "zakera_backups" {
  bucket = aws_s3_bucket.zakera_backups.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "zakera_backups" {
  bucket = aws_s3_bucket.zakera_backups.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "zakera_backups" {
  bucket = aws_s3_bucket.zakera_backups.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Logs bucket
resource "aws_s3_bucket" "zakera_logs" {
  bucket = "${var.project_name}-${var.environment}-logs-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name        = "${var.project_name}-logs"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_encryption" "zakera_logs" {
  bucket = aws_s3_bucket.zakera_logs.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "zakera_logs" {
  bucket = aws_s3_bucket.zakera_logs.id
  
  rule {
    id     = "archive-logs"
    status = "Enabled"
    
    transition {
      days          = 30
      storage_class = "GLACIER"
    }
    
    expiration {
      days = 90
    }
  }
}

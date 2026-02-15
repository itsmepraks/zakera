#!/bin/bash
# Database and configuration backup script
# Usage: ./backup.sh [staging|production]

set -e

ENVIRONMENT=${1:-staging}
BACKUP_DIR="backups/${ENVIRONMENT}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Creating backup for ${ENVIRONMENT}"

# Create backup directory
mkdir -p $BACKUP_DIR

# Load environment variables
if [ -f ".env.${ENVIRONMENT}" ]; then
    export $(cat .env.${ENVIRONMENT} | grep -v '^#' | xargs)
fi

# Backup database
echo "Backing up database..."
pg_dump $DATABASE_URL | gzip > "${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz"

# Backup Redis (if applicable)
if [ -n "$REDIS_URL" ]; then
    echo "Backing up Redis..."
    redis-cli --rdb "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb" || echo "Redis backup skipped"
fi

# Backup configuration files
echo "Backing up configuration..."
tar -czf "${BACKUP_DIR}/config_${TIMESTAMP}.tar.gz" \
    .env.${ENVIRONMENT} \
    config/ \
    monitoring/ \
    2>/dev/null || echo "Config backup completed with warnings"

# Upload to S3 (if configured)
if [ -n "$BACKUP_S3_BUCKET" ]; then
    echo "Uploading backups to S3..."
    aws s3 sync $BACKUP_DIR s3://${BACKUP_S3_BUCKET}/zakera/${ENVIRONMENT}/ \
        --storage-class STANDARD_IA
fi

# Clean up old backups (keep last 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_DIR}"
ls -lh $BACKUP_DIR | tail -5

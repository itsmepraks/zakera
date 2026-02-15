#!/bin/bash
# Database migration script
# Usage: ./migrate.sh [staging|production]

set -e

ENVIRONMENT=${1:-staging}

echo "Running database migrations for ${ENVIRONMENT}"

# Load environment variables
if [ -f ".env.${ENVIRONMENT}" ]; then
    export $(cat .env.${ENVIRONMENT} | xargs)
fi

# Validate database connection
echo "Testing database connection..."
python -c "from src.api.database import engine; import asyncio; asyncio.run(engine.connect())" || {
    echo "Failed to connect to database"
    exit 1
}

# Create backup before migration
echo "Creating database backup..."
timestamp=$(date +%Y%m%d_%H%M%S)
backup_file="backup_${ENVIRONMENT}_${timestamp}.sql"

if [ "$ENVIRONMENT" = "production" ]; then
    pg_dump $DATABASE_URL > "backups/${backup_file}"
    echo "Backup created: ${backup_file}"
fi

# Run migrations
echo "Running Alembic migrations..."
alembic upgrade head

echo "Migrations completed successfully!"

# Verify migration
echo "Verifying database schema..."
alembic current

#!/bin/bash

# Database Backup Script for Supabase
# Usage: ./backup_database.sh [staging|production]
# Backs up database to S3 with timestamp versioning

set -e

# Configuration
BACKUP_ENV=${1:-staging}
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILENAME="supabase_${BACKUP_ENV}_${BACKUP_DATE}.sql.gz"
BACKUP_DIR="${HOME}/.supabase_backups"
S3_BUCKET="s3://b3-options-signals-backups"
S3_PATH="${S3_BUCKET}/${BACKUP_ENV}/${BACKUP_FILENAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate environment
if [ "$BACKUP_ENV" != "staging" ] && [ "$BACKUP_ENV" != "production" ]; then
  echo -e "${RED}Error: Invalid environment. Use 'staging' or 'production'${NC}"
  exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo -e "${YELLOW}[$(date)] Starting backup of ${BACKUP_ENV} database...${NC}"

# Step 1: Dump database (using Supabase CLI or pg_dump)
echo -e "${YELLOW}Step 1: Dumping database...${NC}"

# Option A: Using Supabase CLI (if installed)
if command -v supabase &> /dev/null; then
  echo "Using Supabase CLI..."
  supabase db dump --db-url "$SUPABASE_DB_URL" | gzip > "$BACKUP_DIR/$BACKUP_FILENAME"
else
  # Option B: Using pg_dump (requires pg_dump installed)
  echo "Using pg_dump..."
  DB_URL="${SUPABASE_DB_URL}"
  if [ -z "$DB_URL" ]; then
    echo -e "${RED}Error: SUPABASE_DB_URL not set${NC}"
    exit 1
  fi
  pg_dump "$DB_URL" | gzip > "$BACKUP_DIR/$BACKUP_FILENAME"
fi

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Database dumped${NC}"
else
  echo -e "${RED}✗ Database dump failed${NC}"
  exit 1
fi

# Step 2: Verify backup file
echo -e "${YELLOW}Step 2: Verifying backup...${NC}"
if [ -f "$BACKUP_DIR/$BACKUP_FILENAME" ]; then
  BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILENAME" | cut -f1)
  echo -e "${GREEN}✓ Backup created (size: ${BACKUP_SIZE})${NC}"
else
  echo -e "${RED}✗ Backup file not found${NC}"
  exit 1
fi

# Step 3: Upload to S3 (if AWS credentials available)
echo -e "${YELLOW}Step 3: Uploading to S3...${NC}"

if command -v aws &> /dev/null; then
  # Check if S3 bucket exists
  if aws s3 ls "${S3_BUCKET}" > /dev/null 2>&1; then
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILENAME" "$S3_PATH" --storage-class STANDARD_IA
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}✓ Backup uploaded to ${S3_PATH}${NC}"

      # Verify upload
      if aws s3 ls "$S3_PATH" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Upload verified${NC}"
      else
        echo -e "${RED}✗ Upload verification failed${NC}"
        exit 1
      fi
    else
      echo -e "${RED}✗ S3 upload failed${NC}"
      exit 1
    fi
  else
    echo -e "${YELLOW}⚠ S3 bucket not accessible (credentials missing)${NC}"
    echo "Backup saved locally at: $BACKUP_DIR/$BACKUP_FILENAME"
  fi
else
  echo -e "${YELLOW}⚠ AWS CLI not installed. Backup saved locally only.${NC}"
fi

# Step 4: Cleanup (keep last 7 days locally)
echo -e "${YELLOW}Step 4: Cleaning up old backups...${NC}"
KEEP_DAYS=7
find "$BACKUP_DIR" -name "supabase_${BACKUP_ENV}_*.sql.gz" -mtime +$KEEP_DAYS -delete
echo -e "${GREEN}✓ Old backups cleaned (keeping last ${KEEP_DAYS} days)${NC}"

# Summary
echo -e "${GREEN}[$(date)] Backup completed successfully!${NC}"
echo ""
echo "Summary:"
echo "  Environment: $BACKUP_ENV"
echo "  Backup file: $BACKUP_FILENAME"
echo "  Size: $BACKUP_SIZE"
echo "  Location: $BACKUP_DIR"
echo "  S3 path: $S3_PATH"
echo ""

# Log the backup
LOG_FILE="$BACKUP_DIR/backup.log"
echo "[$(date)] Backup $BACKUP_ENV completed: $BACKUP_FILENAME ($BACKUP_SIZE)" >> "$LOG_FILE"

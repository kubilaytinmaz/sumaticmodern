#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - Backup Script
# =============================================================================
# Usage: ./deployment/backup.sh [options]
# Options:
#   --full        Full backup (database + redis + configs)
#   --db-only     Database backup only
#   --redis-only  Redis backup only
#   --retention N Keep last N backups (default: 7)
# =============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_DIR=$(date +%Y-%m-%d)

# Container names
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-sumatic-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-sumatic-redis}"

# Database credentials
DB_USER="${POSTGRES_USER:-sumatic}"
DB_NAME="${POSTGRES_DB:-sumatic_db}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
BACKUP_TYPE="full"
while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            BACKUP_TYPE="full"
            shift
            ;;
        --db-only)
            BACKUP_TYPE="db"
            shift
            ;;
        --redis-only)
            BACKUP_TYPE="redis"
            shift
            ;;
        --retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create backup directory
mkdir -p "${BACKUP_DIR}/${DATE_DIR}"

echo -e "${BLUE}=============================================="
echo " Sumatic Modern IoT - Backup Script"
echo "==============================================${NC}"
echo ""
echo "Timestamp: ${TIMESTAMP}"
echo "Backup Type: ${BACKUP_TYPE}"
echo "Backup Directory: ${BACKUP_DIR}/${DATE_DIR}"
echo "Retention: ${RETENTION_DAYS} days"
echo ""

# ---------------------------------------------------------------------------
# PostgreSQL Backup
# ---------------------------------------------------------------------------
backup_postgres() {
    echo -e "${YELLOW}─── PostgreSQL Backup ───${NC}"
    
    local BACKUP_FILE="${BACKUP_DIR}/${DATE_DIR}/postgres_${TIMESTAMP}.sql.gz"
    
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
        echo "Creating PostgreSQL backup..."
        
        # Create backup with pg_dump
        docker exec "$POSTGRES_CONTAINER" pg_dump \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --format=plain \
            --no-owner \
            --no-acl \
            --clean \
            --if-exists \
            | gzip > "$BACKUP_FILE"
        
        local SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}✓ PostgreSQL backup created: ${BACKUP_FILE} (${SIZE})${NC}"
    else
        echo -e "${RED}✗ PostgreSQL is not available${NC}"
        return 1
    fi
    echo ""
}

# ---------------------------------------------------------------------------
# Redis Backup
# ---------------------------------------------------------------------------
backup_redis() {
    echo -e "${YELLOW}─── Redis Backup ───${NC}"
    
    local BACKUP_FILE="${BACKUP_DIR}/${DATE_DIR}/redis_${TIMESTAMP}.rdb"
    
    if docker exec "$REDIS_CONTAINER" redis-cli ping > /dev/null 2>&1; then
        echo "Creating Redis backup..."
        
        # Trigger Redis BGSAVE
        docker exec "$REDIS_CONTAINER" redis-cli BGSAVE
        
        # Wait for save to complete
        sleep 2
        
        # Copy the RDB file
        docker cp "${REDIS_CONTAINER}:/data/dump.rdb" "$BACKUP_FILE"
        
        local SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}✓ Redis backup created: ${BACKUP_FILE} (${SIZE})${NC}"
    else
        echo -e "${RED}✗ Redis is not available${NC}"
        return 1
    fi
    echo ""
}

# ---------------------------------------------------------------------------
# Config Backup
# ---------------------------------------------------------------------------
backup_configs() {
    echo -e "${YELLOW}─── Configuration Backup ───${NC}"
    
    local BACKUP_FILE="${BACKUP_DIR}/${DATE_DIR}/configs_${TIMESTAMP}.tar.gz"
    
    echo "Creating configuration backup..."
    
    # Create temporary directory for configs
    local TEMP_DIR=$(mktemp -d)
    
    # Copy configuration files
    cp -r mqtt-broker "$TEMP_DIR/" 2>/dev/null || true
    cp deployment/nginx.conf "$TEMP_DIR/" 2>/dev/null || true
    cp .env.example "$TEMP_DIR/" 2>/dev/null || true
    cp docker-compose.yml "$TEMP_DIR/" 2>/dev/null || true
    cp docker-compose.prod.yml "$TEMP_DIR/" 2>/dev/null || true
    
    # Create archive
    tar -czf "$BACKUP_FILE" -C "$TEMP_DIR" . 2>/dev/null
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    
    local SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Configuration backup created: ${BACKUP_FILE} (${SIZE})${NC}"
    echo ""
}

# ---------------------------------------------------------------------------
# Retention Policy
# ---------------------------------------------------------------------------
apply_retention() {
    echo -e "${YELLOW}─── Applying Retention Policy ───${NC}"
    
    echo "Removing backups older than ${RETENTION_DAYS} days..."
    
    # Find and delete old backups
    find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
    find "$BACKUP_DIR" -type f -name "*.rdb" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
    find "$BACKUP_DIR" -type f -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
    
    # Remove empty directories
    find "$BACKUP_DIR" -type d -empty -delete 2>/dev/null || true
    
    echo -e "${GREEN}✓ Retention policy applied${NC}"
    echo ""
}

# ---------------------------------------------------------------------------
# Backup Summary
# ---------------------------------------------------------------------------
show_summary() {
    echo -e "${BLUE}=============================================="
    echo " Backup Summary"
    echo "==============================================${NC}"
    
    echo ""
    echo "Backup files created in: ${BACKUP_DIR}/${DATE_DIR}"
    echo ""
    echo "Files:"
    ls -lh "${BACKUP_DIR}/${DATE_DIR}/" 2>/dev/null || echo "  No files"
    echo ""
    
    # Calculate total size
    local TOTAL_SIZE=$(du -sh "${BACKUP_DIR}/${DATE_DIR}" 2>/dev/null | cut -f1)
    echo "Total backup size: ${TOTAL_SIZE}"
    echo ""
    
    # Show disk usage
    echo "Disk usage:"
    df -h "${BACKUP_DIR}" 2>/dev/null | tail -1
    echo ""
}

# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------
main() {
    case "$BACKUP_TYPE" in
        full)
            backup_postgres
            backup_redis
            backup_configs
            ;;
        db)
            backup_postgres
            ;;
        redis)
            backup_redis
            ;;
    esac
    
    apply_retention
    show_summary
    
    echo -e "${GREEN}Backup completed successfully!${NC}"
}

# Run main function
main

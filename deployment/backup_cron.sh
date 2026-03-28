#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - Automated Backup Cron Script
# =============================================================================
# This script is designed to be run via cron for automated backups
# 
# Cron Schedule Examples:
#   - Daily at 2 AM:         0 2 * * * /path/to/deployment/backup_cron.sh
#   - Every 6 hours:        0 */6 * * * /path/to/deployment/backup_cron.sh
#   - Weekly on Sunday:     0 2 * * 0 /path/to/deployment/backup_cron.sh
#
# Setup:
#   1. Make executable: chmod +x deployment/backup_cron.sh
#   2. Add to crontab: crontab -e
#   3. Add line: 0 2 * * * /path/to/deployment/backup_cron.sh >> /var/log/sumatic_backup.log 2>&1
# =============================================================================

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Log file
LOG_FILE="${LOG_FILE:-./logs/backup_cron.log}"
LOG_RETENTION_DAYS="${LOG_RETENTION_DAYS:-30}"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handling
trap 'log "ERROR: Backup failed at line $LINENO"' ERR

log "=========================================="
log "Starting automated backup"
log "=========================================="

# Run the main backup script
if bash deployment/backup.sh --full; then
    log "Backup completed successfully"
    
    # Clean old log files
    find "$(dirname "$LOG_FILE")" -name "*.log" -type f -mtime +${LOG_RETENTION_DAYS} -delete 2>/dev/null || true
    
    log "Log cleanup completed (retention: ${LOG_RETENTION_DAYS} days)"
else
    log "ERROR: Backup script failed with exit code $?"
    exit 1
fi

log "=========================================="
log "Automated backup finished"
log "=========================================="

exit 0

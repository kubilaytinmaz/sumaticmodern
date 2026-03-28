#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - SQLite to PostgreSQL Migration Script
# =============================================================================
# This script migrates data from SQLite to PostgreSQL database
# Usage: ./migrate_to_postgresql.sh [source_db] [target_connection_string]
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parameters
SOURCE_DB="${1:-$PROJECT_ROOT/backend/sumatic_modern.db}"
TARGET_DB="${2:-postgresql://sumatic:password@localhost:5432/sumatic_modern}"

# Functions
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

usage() {
    cat << EOF
${BLUE}SQLite to PostgreSQL Migration${NC}

${YELLOW}Usage:${NC}
    $0 [source_db] [target_connection_string]

${YELLOW}Parameters:${NC}
    source_db              - Path to SQLite database (default: backend/sumatic_modern.db)
    target_connection      - PostgreSQL connection string

${YELLOW}Examples:${NC}
    $0 backend/sumatic_modern.db postgresql://user:pass@localhost:5432/dbname
    $0 ./data.db postgresql://sumatic:secure_pass@db-server:5432/sumatic_prod

${YELLOW}Prerequisites:${NC}
    - PostgreSQL server running and accessible
    - Target database created
    - Python 3.9+ with required packages
    - SQLite database file exists

${YELLOW}Connection String Format:${NC}
    postgresql://username:password@host:port/database
EOF
    exit 1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required"
        exit 1
    fi
    
    # Check SQLite database exists
    if [ ! -f "$SOURCE_DB" ]; then
        print_error "SQLite database not found: $SOURCE_DB"
        exit 1
    fi
    print_success "SQLite database found"
    
    # Check required Python packages
    print_info "Checking Python packages..."
    python3 -c "import sqlalchemy" 2>/dev/null || {
        print_error "SQLAlchemy not installed. Run: pip install sqlalchemy"
        exit 1
    }
    python3 -c "import psycopg2" 2>/dev/null || {
        print_error "psycopg2 not installed. Run: pip install psycopg2-binary"
        exit 1
    }
    print_success "Python packages OK"
}

# Test PostgreSQL connection
test_postgres_connection() {
    print_info "Testing PostgreSQL connection..."
    
    python3 << EOF
import sys
from sqlalchemy import create_engine, text

try:
    engine = create_engine("$TARGET_DB")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✓ PostgreSQL connection successful")
    sys.exit(0)
except Exception as e:
    print(f"✗ PostgreSQL connection failed: {e}")
    sys.exit(1)
EOF
    
    if [ $? -ne 0 ]; then
        print_error "Cannot connect to PostgreSQL"
        exit 1
    fi
    print_success "PostgreSQL connection OK"
}

# Create PostgreSQL schema
create_schema() {
    print_info "Creating PostgreSQL schema..."
    
    cd "$PROJECT_ROOT/backend"
    
    # Run Alembic migrations
    python3 -m alembic upgrade head
    
    if [ $? -eq 0 ]; then
        print_success "Schema created successfully"
    else
        print_error "Failed to create schema"
        exit 1
    fi
}

# Migrate data
migrate_data() {
    print_info "Migrating data from SQLite to PostgreSQL..."
    
    python3 << EOF
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Source (SQLite)
source_engine = create_engine("sqlite:///$SOURCE_DB")
SourceSession = sessionmaker(bind=source_engine)

# Target (PostgreSQL)
target_engine = create_engine("$TARGET_DB")
TargetSession = sessionmaker(bind=target_engine)

# Get list of tables
with source_engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = [row[0] for row in result if not row[0].startswith('sqlite_') and row[0] != 'alembic_version']

print(f"Found {len(tables)} tables to migrate")

# Migrate each table
for table in tables:
    print(f"Migrating {table}...")
    
    source_session = SourceSession()
    target_session = TargetSession()
    
    try:
        # Read all data from source
        with source_engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table}"))
            rows = result.fetchall()
            columns = result.keys()
        
        if not rows:
            print(f"  No data in {table}, skipping")
            continue
        
        # Get column names
        with source_engine.connect() as conn:
            result = conn.execute(text(f"PRAGMA table_info({table})"))
            column_info = result.fetchall()
        
        # Build INSERT statement
        column_names = [col[1] for col in column_info]
        placeholders = ', '.join([':' + col for col in column_names])
        insert_sql = f"INSERT INTO {table} ({', '.join(column_names)}) VALUES ({placeholders})"
        
        # Insert data into target
        with target_engine.connect() as conn:
            for row in rows:
                row_dict = dict(zip(column_names, row))
                conn.execute(text(insert_sql), row_dict)
            conn.commit()
        
        print(f"  ✓ Migrated {len(rows)} rows from {table}")
        
    except Exception as e:
        print(f"  ✗ Error migrating {table}: {e}")
        target_session.rollback()
    finally:
        source_session.close()
        target_session.close()

print("✓ Data migration completed")
EOF

    if [ $? -eq 0 ]; then
        print_success "Data migration completed"
    else
        print_error "Data migration failed"
        exit 1
    fi
}

# Verify migration
verify_migration() {
    print_info "Verifying migration..."
    
    python3 << EOF
from sqlalchemy import create_engine, text

source_engine = create_engine("sqlite:///$SOURCE_DB")
target_engine = create_engine("$TARGET_DB")

tables_to_check = ['users', 'devices', 'device_readings', 'device_hourly_status', 'device_status_snapshots']

print("\nRow count comparison:")
print(f"{'Table':<30} {'SQLite':<15} {'PostgreSQL':<15} {'Status':<10}")
print("-" * 70)

all_match = True
for table in tables_to_check:
    try:
        with source_engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            source_count = result.scalar()
    except:
        source_count = 0
    
    try:
        with target_engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            target_count = result.scalar()
    except:
        target_count = 0
    
    status = "✓" if source_count == target_count else "✗"
    if source_count != target_count:
        all_match = False
    
    print(f"{table:<30} {source_count:<15} {target_count:<15} {status:<10}")

print("-" * 70)
if all_match:
    print("✓ All tables match!")
else:
    print("✗ Some tables have mismatched row counts")
EOF
}

# Update environment configuration
update_env_file() {
    print_info "Updating environment configuration..."
    
    ENV_FILE="$PROJECT_ROOT/backend/.env.production"
    
    if [ -f "$ENV_FILE" ]; then
        # Backup existing file
        cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Update DATABASE_URL
        if grep -q "^DATABASE_URL=" "$ENV_FILE"; then
            sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$TARGET_DB|" "$ENV_FILE"
        else
            echo "DATABASE_URL=$TARGET_DB" >> "$ENV_FILE"
        fi
        
        print_success "Environment file updated"
        print_warning "Backup saved as: $ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    else
        print_warning "Environment file not found: $ENV_FILE"
        print_info "Create .env.production with DATABASE_URL=$TARGET_DB"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║     Sumatic Modern IoT - SQLite to PostgreSQL Migration       ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Validate parameters
    if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
        usage
    fi
    
    print_info "Source database: $SOURCE_DB"
    print_info "Target database: $TARGET_DB"
    echo ""
    
    # Confirmation
    print_warning "This will migrate data from SQLite to PostgreSQL"
    read -p "Continue? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        print_info "Migration cancelled"
        exit 0
    fi
    
    # Execute migration
    check_prerequisites
    test_postgres_connection
    create_schema
    migrate_data
    verify_migration
    update_env_file
    
    echo ""
    print_success "Migration completed successfully!"
    echo ""
    print_info "Next steps:"
    echo "  1. Update docker-compose.yml to use PostgreSQL"
    echo "  2. Restart the application"
    echo "  3. Verify all functionality"
    echo "  4. Keep SQLite database as backup"
    echo ""
}

# Run main
main "$@"

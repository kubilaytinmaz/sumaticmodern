#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - Health Check Script
# =============================================================================
# Usage: ./deployment/healthcheck.sh
# Returns: 0 if all services are healthy, 1 otherwise
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-sumatic-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-sumatic-redis}"
MQTT_CONTAINER="${MQTT_CONTAINER:-sumatic-mqtt}"

# Track overall status
OVERALL_STATUS=0

# Helper function
check_service() {
    local service_name=$1
    local status=$2
    
    if [ "$status" -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} ${service_name}: OK"
    else
        echo -e "  ${RED}✗${NC} ${service_name}: FAILED"
        OVERALL_STATUS=1
    fi
}

echo "=============================================="
echo " Sumatic Modern IoT - Health Check"
echo "=============================================="
echo ""
echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""

# ---------------------------------------------------------------------------
# 1. PostgreSQL Health Check
# ---------------------------------------------------------------------------
echo "─── Database (PostgreSQL + TimescaleDB) ───"
if docker exec "$POSTGRES_CONTAINER" pg_isready -U sumatic -d sumatic_db > /dev/null 2>&1; then
    check_service "PostgreSQL Connection" 0
else
    check_service "PostgreSQL Connection" 1
fi

# Check TimescaleDB extension
if docker exec "$POSTGRES_CONTAINER" psql -U sumatic -d sumatic_db -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb'" > /dev/null 2>&1; then
    check_service "TimescaleDB Extension" 0
else
    check_service "TimescaleDB Extension" 1
fi
echo ""

# ---------------------------------------------------------------------------
# 2. Redis Health Check
# ---------------------------------------------------------------------------
echo "─── Cache (Redis) ───"
if docker exec "$REDIS_CONTAINER" redis-cli ping > /dev/null 2>&1; then
    check_service "Redis Connection" 0
else
    check_service "Redis Connection" 1
fi

# Check Redis memory usage
REDIS_MEMORY=$(docker exec "$REDIS_CONTAINER" redis-cli info memory 2>/dev/null | grep used_memory_human | tr -d '\r' | cut -d: -f2)
if [ -n "$REDIS_MEMORY" ]; then
    echo "  Memory usage: $REDIS_MEMORY"
fi
echo ""

# ---------------------------------------------------------------------------
# 3. MQTT Health Check
# ---------------------------------------------------------------------------
echo "─── MQTT Broker (Mosquitto) ───"
if docker exec "$MQTT_CONTAINER" mosquitto_sub -t '$SYS/#' -C 1 -W 3 > /dev/null 2>&1; then
    check_service "Mosquitto Broker" 0
else
    check_service "Mosquitto Broker" 1
fi
echo ""

# ---------------------------------------------------------------------------
# 4. Backend Health Check
# ---------------------------------------------------------------------------
echo "─── Backend API (FastAPI) ───"
BACKEND_RESPONSE=$(curl -sf "${BACKEND_URL}/health" 2>/dev/null || echo "FAILED")
if [ "$BACKEND_RESPONSE" != "FAILED" ]; then
    check_service "Backend API" 0
    
    # Parse health response
    DB_STATUS=$(echo "$BACKEND_RESPONSE" | python3 -c "import sys,json;print(json.load(sys.stdin).get('database','unknown'))" 2>/dev/null || echo "unknown")
    REDIS_STATUS=$(echo "$BACKEND_RESPONSE" | python3 -c "import sys,json;print(json.load(sys.stdin).get('redis','unknown'))" 2>/dev/null || echo "unknown")
    MQTT_STATUS=$(echo "$BACKEND_RESPONSE" | python3 -c "import sys,json;print(json.load(sys.stdin).get('mqtt','unknown'))" 2>/dev/null || echo "unknown")
    
    echo "  Database: $DB_STATUS"
    echo "  Redis: $REDIS_STATUS"
    echo "  MQTT: $MQTT_STATUS"
else
    check_service "Backend API" 1
fi
echo ""

# ---------------------------------------------------------------------------
# 5. Frontend Health Check
# ---------------------------------------------------------------------------
echo "─── Frontend (Next.js) ───"
if curl -sf "${FRONTEND_URL}" > /dev/null 2>&1; then
    check_service "Frontend App" 0
else
    check_service "Frontend App" 1
fi
echo ""

# ---------------------------------------------------------------------------
# 6. Docker Container Status
# ---------------------------------------------------------------------------
echo "─── Docker Container Status ───"
docker ps --format "  {{.Names}}: {{.Status}}" --filter "name=sumatic" 2>/dev/null || echo "  Could not retrieve container status"
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "=============================================="
if [ "$OVERALL_STATUS" -eq 0 ]; then
    echo -e "  ${GREEN}All services are healthy${NC}"
else
    echo -e "  ${RED}Some services have issues${NC}"
fi
echo "=============================================="

exit $OVERALL_STATUS

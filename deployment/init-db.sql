-- =============================================================================
-- Sumatic Modern IoT - Database Initialization Script
-- =============================================================================
-- This script runs automatically when PostgreSQL container starts for the first time
-- =============================================================================

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- =============================================================================
-- Create initial admin user (password: admin123 - CHANGE THIS!)
-- =============================================================================
-- Note: This is a placeholder. In production, create users through the API
-- or use a more secure method.
-- =============================================================================

-- The actual user creation will be handled by the application's Alembic migrations
-- This script ensures TimescaleDB is ready and creates any necessary extensions

-- =============================================================================
-- Create indexes for better performance
-- =============================================================================

-- Index on readings table for time-based queries
-- Note: These will be created by Alembic migrations, but we ensure they exist

-- =============================================================================
-- Create continuous aggregates for analytics
-- =============================================================================

-- These will be created by the application's migration system
-- See backend/alembic/versions/ for actual migrations

-- =============================================================================
-- Grant permissions (if needed)
-- =============================================================================

-- Ensure the application user has necessary permissions
GRANT ALL PRIVILEGES ON DATABASE sumatic_db TO sumatic;
GRANT ALL PRIVILEGES ON SCHEMA public TO sumatic;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sumatic;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sumatic;

-- =============================================================================
-- TimescaleDB hypertable configuration
-- =============================================================================

-- The readings table will be converted to a hypertable by the application
-- This is just a placeholder for reference

-- =============================================================================
-- Sample data (optional - for development only)
-- =============================================================================

-- Uncomment the following for development/testing:

-- INSERT INTO devices (name, device_type, modbus_address, port, register_count, is_active) VALUES
-- ('Test Device 1', 'energy_meter', '192.168.1.100', 502, 10, true),
-- ('Test Device 2', 'water_meter', '192.168.1.101', 502, 5, true);

-- =============================================================================
-- Database version info
-- =============================================================================

-- Create a table to track database initialization
CREATE TABLE IF NOT EXISTS _db_info (
    key VARCHAR(100) PRIMARY KEY,
    value VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO _db_info (key, value) VALUES
    ('initialized', 'true'),
    ('timescaledb_version', (SELECT extversion FROM pg_extension WHERE extname = 'timescaledb')),
    ('init_script_version', '1.0.0')
ON CONFLICT (key) DO NOTHING;

-- =============================================================================
-- End of initialization script
-- =============================================================================

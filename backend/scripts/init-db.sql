-- UcharMarket Database Initialization Script
-- This script runs on PostgreSQL container initialization

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable PostGIS for geospatial queries (optional, for map features)
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- Create custom types (if not using SQLAlchemy Enum)
-- These are created by Alembic migrations, but we include them here for reference

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ucharmarket TO ucharmarket;

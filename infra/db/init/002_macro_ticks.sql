-- Migration: Add macro_ticks hypertable for Protocol #3 (Macro Context)
-- Auto-executed on container startup via /docker-entrypoint-initdb.d/

-- Create Macro Ticks Table
CREATE TABLE IF NOT EXISTS macro_ticks (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    value       DOUBLE PRECISION,
    regime_tag  TEXT
);

-- Convert to Hypertable
SELECT create_hypertable('macro_ticks', 'time', if_not_exists => TRUE);

-- Create Index for Fast Symbol Queries
CREATE INDEX IF NOT EXISTS idx_macro_ticks_symbol_time ON macro_ticks (symbol, time DESC);

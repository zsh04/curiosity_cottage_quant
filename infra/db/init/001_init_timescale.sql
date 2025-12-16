-- TimescaleDB Initialization Script
-- Auto-executed on container startup via /docker-entrypoint-initdb.d/

-- Step 1: Enable TimescaleDB Extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Step 2: Create Market Ticks Table
CREATE TABLE IF NOT EXISTS market_ticks (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    price       DOUBLE PRECISION,
    volume      DOUBLE PRECISION
);

-- Step 3: Convert to Hypertable
-- Partitions data by time for optimal time-series performance
SELECT create_hypertable('market_ticks', 'time', if_not_exists => TRUE);

-- Step 4: Create Index for Fast Symbol Queries
-- Optimized for queries like: SELECT * FROM market_ticks WHERE symbol = 'SPY' ORDER BY time DESC
CREATE INDEX IF NOT EXISTS idx_market_ticks_symbol_time ON market_ticks (symbol, time DESC);

-- Optional: Set compression policy (uncomment if needed for production)
-- ALTER TABLE market_ticks SET (
--     timescaledb.compress,
--     timescaledb.compress_segmentby = 'symbol'
-- );
-- SELECT add_compression_policy('market_ticks', INTERVAL '7 days');

-- Optional: Set retention policy (uncomment if needed)
-- SELECT add_retention_policy('market_ticks', INTERVAL '1 year');

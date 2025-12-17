-- Step 5: Enable Compression
-- Compress data to save space (90%+ savings typical)
-- Segment by symbol to keep related data together
ALTER TABLE market_ticks SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);

-- Step 6: Add Compression Policy
-- Compress chunks strictly older than 7 days
SELECT add_compression_policy('market_ticks', INTERVAL '7 days');

-- Step 7: Add Retention Policy
-- Drop raw tick data older than 30 days (High Frequency data expires fast)
-- We assume aggregated candles are stored elsewhere or we only need recent history for this MVP
SELECT add_retention_policy('market_ticks', INTERVAL '30 days');

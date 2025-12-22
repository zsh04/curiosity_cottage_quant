-- PHSE 34.1: THE SCROLLS OF HERODOTUS (Backtest Audit)
-- Identity: Herodotus (The Historian)
-- Goal: Immutable Event Log for Simulations

-- TASK 1: THE EVENT LOG
-- Tracks lifecycle: SPAWNED, STARTED, COMPLETED, FAILED
CREATE TABLE IF NOT EXISTS backtest_events (
    ts TIMESTAMP,
    run_id SYMBOL,
    ticker SYMBOL,
    event_type SYMBOL,
    payload STRING
) TIMESTAMP(ts) PARTITION BY MONTH;

-- TASK 2: THE EQUITY CURVE
-- Tracks equity over time for performance and drawdown calc
CREATE TABLE IF NOT EXISTS backtest_equity (
    ts TIMESTAMP,
    run_id SYMBOL,
    equity DOUBLE,
    cash DOUBLE,
    pnl DOUBLE
) TIMESTAMP(ts) PARTITION BY MONTH;

-- TASK 3: MARKET TICKS (High-Frequency Data)
-- Replaces legacy Postgres MarketTick
CREATE TABLE IF NOT EXISTS market_ticks (
    ts TIMESTAMP,
    symbol SYMBOL,
    price DOUBLE,
    volume DOUBLE,
    side SYMBOL,
    condition SYMBOL
) TIMESTAMP(ts) PARTITION BY DAY;

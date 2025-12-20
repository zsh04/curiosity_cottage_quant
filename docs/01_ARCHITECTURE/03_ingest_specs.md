# Service Specification: The Siphon (Ingest)

**Type:** FastStream Application (Host/Docker)
**Role:** Market Data Normalization & Ingestion
**Cycle:** Real-time (Streaming)

## Interface

* **Input:** Alpaca `StockDataStream` (Websocket via `iex` feed)
* **Output Topic:** `market.tick.{symbol}` (Publishes `EzekielTick`)

## Data Structures

### EzekielTick Schema

```json
{
  "symbol": "string",
  "price": "float",
  "size": "float",
  "timestamp": "string (iso8601)",
  "updates": "integer",
  "exchange": "string"
}
```

## Resilience Strategy

* **Pipeline Repair:** Infinite loop with `try/except`.
* **Backoff:** 5-second sleep on connection rupture.
* **Logging:** Captures "Spills" (Extraction errors) without crashing the main loop.

## Configuration

* **Vault:** `ALPACA_API_KEY`, `ALPACA_API_SECRET`
* **Feed:** Defined by `ALPACA_DATA_FEED` (Default: `iex`)
* **Scope:** `WATCHLIST` (e.g., `["SPY", "NVDA", "AAPL"]`)

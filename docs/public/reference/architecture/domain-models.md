# Service Specification: Data Models

**Type:** Schemas (Pydantic & SQLAlchemy)
**Role:** Domain Entities & Persistence
**Location:** `app/core/models.py`, `app/dal/models.py`

## 1. Domain Entities (The Nervous System)

These Pydantic models define the "Packets" that flow between services.

### ForceVector (`physics.forces`)

The output of the Feynman (Physics) Service.

```json
{
  "timestamp": "datetime",
  "symbol": "str",
  "mass": "float (Volume * CLV)",
  "momentum": "float (Mass * Velocity)",
  "friction": "float (TradeCount / Volume)",
  "entropy": "float (Shannon Entropy)",
  "nash_dist": "float (Z-Score)",
  "price": "float",
  "alpha_coefficient": "float (Tail Index)"
}
```

### TradeSignal (`soros.signals`)

The output of the Soros (Reasoning) Service.

```json
{
  "timestamp": "datetime",
  "symbol": "str",
  "side": "enum(BUY, SELL, HOLD)",
  "strength": "float (0.0 - 1.0)",
  "price": "float",
  "quantity": "float (Optional)",
  "meta": "dict (Reasoning Logs)"
}
```

### OrderPacket (`execution.orders`)

The output of the Risk Gate, sent to Execution.

```json
{
  "timestamp": "datetime",
  "signal_id": "str (UUID)",
  "symbol": "str",
  "side": "str",
  "quantity": "float",
  "order_type": "str (Default: MARKET)",
  "risk_check_passed": "bool"
}
```

### ForecastPacket (`chronos.forecasts`)

The output of the Chronos (Time-Series) Service.

```json
{
  "timestamp": "datetime",
  "symbol": "str",
  "p10": "float",
  "p50": "float",
  "p90": "float",
  "horizon": "int",
  "confidence": "float",
  "is_synthetic": "bool"
}
```

## 2. Persistence Models (The Memory)

These SQLAlchemy models define the tables in Postgres/TimescaleDB.

### AgentStateSnapshot

Captures the full state of an agent's brain after every cycle.

* **Fields:** `nav`, `cash`, `daily_pnl`, `max_drawdown`, `symbol`, `price`, `current_alpha`, `regime`, `velocity`, `acceleration`, `signal_side`, `signal_confidence`, `reasoning`.

### MarketStateEmbedding

Stores high-dimensional vectors for RAG (Retrieval Augmented Generation).

* **Fields:** `timestamp`, `symbol`, `embedding` (Vector-1536), `metadata` (JSON).
* **Index:** HNSW for fast similarity search.

### AgentPerformanceMetrics

Logs latency and success/failure for every agent cycle.

* **Fields:** `agent_name`, `latency_ms`, `success`, `error_message`, `output_data` (JSON).

### ModelPerformanceMetrics

Logs inference stats for AI models (LLMs, FinBERT, Chronos).

* **Fields:** `model_name`, `invocation_latency_ms`, `tokens_input`, `tokens_output`, `thought_process`, `confidence`.

### TradeJournal

Audit trail of all executions (Requested vs Filled).

* **Fields:** `symbol`, `side`, `requested_size`, `filled_size`, `slippage_bps`, `execution_latency_ms`, `alpha_at_execution`.

### MarketTick / MacroTick (Hypertable)

Time-series data for Price and Macro Indicators (US10Y, VIX).

* **Engine:** QuestDB (Backfill & Realtime).
* **Table:** `trades`
  * `symbol` (SYMBOL)
  * `price` (DOUBLE)
  * `size` (DOUBLE)
  * `timestamp` (TIMESTAMP) (Designated Timestamp)
  * `conditions` (STRING)
  * `tape` (SYMBOL)
* **Table:** `ohlcv_1d`
  * `symbol` (SYMBOL)
  * `open`, `high`, `low`, `close` (DOUBLE)
  * `volume` (LONG)
  * `timestamp` (TIMESTAMP)

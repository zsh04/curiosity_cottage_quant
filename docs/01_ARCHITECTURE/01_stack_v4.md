# The War Stack (v4.0)

## The Core (Reflexes)

* **Language:** Python 3.11+
* **Speed:** `uvloop` (Event Loop), `orjson` (JSON).
* **Data:** `Polars` (Dataframes), `NumPy` (Ring Buffers).
* **State:** `Redis` (Hot Memory).

## The Cortex (Intelligence)

* **Forecasting:** Chronos-Bolt (Async Service).
* **Sentiment:** FinBERT (Async Service).

## The Storage (Memory)

* **Hot:** Redis.
* **Cold:** TimescaleDB (PostgreSQL).
* **Deep:** TimescaleVector (pgvector).

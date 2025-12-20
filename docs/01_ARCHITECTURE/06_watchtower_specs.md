# Service Specification: Watchtower (Heimdall)

**Type:** Infrastructure / Observability
**Role:** The All-Seeing Eye (Real-Time UI Bridge)
**Cycle:** Continuous (Streaming)

## Interface

* **Input Channels:**
  * `physics.forces` (Market Dynamics)
  * `forecast.signals` (Chronos Predictions)
  * `strategy.signals` (Soros Decisions)
* **Output:** Websocket Stream (`ws://host:port/ws/stream`)

## Components

### 1. Redis Bridge (`app/services/redis_bridge.py`)

* **Function:** Listens to Redis PubSub channels using `redis-py` (async).
* **Transformation:** Maps raw internal contracts (`ForceVector`, `ForecastPacket`) to UI-optimized JSON structure.
* **Derived Metrics:**
  * **Regime:** Gaussian (Alpha > 2.0) vs Lévy Stable (1.5 < Alpha <= 2.0) vs Critical (Alpha <= 1.5).
  * **Sentiment:** Aggregated score from Bull/Bear signals.

### 2. BrainStream (`app/api/routes/websocket.py`)

* **Function:** Litestar Websocket Listener.
* **Mechanism:** Lazy-loads the Redis Bridge on first client connection.
* **Broadcaster:** Uses `StateBroadcaster` (InMemory Queue) to pipe messages from Bridge to connected Clients.

## UI Contract (JSON)

```json
{
  "timestamp": "iso8601",
  "source": "watchtower",
  "market": {
    "symbol": "BTC",
    "price": 50000.0,
    "alpha": 2.5,
    "regime": "GAUSSIAN (Safe)"
  },
  "forecast": {
    "median": [105000.0],
    "p10": [90000.0],
    "p90": [110000.0]
  },
  "signal": {
    "side": "BUY",
    "confidence": 1.0,
    "strategy": "SOROS_TRINITY",
    "reasoning": "{...}" 
  }
}
```

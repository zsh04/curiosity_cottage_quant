# REST API Reference

**Base URL:** `http://localhost:8000/api`  
**Framework:** Litestar (Python)  
**Authentication:** None (internal use only)

---

## Overview

| Controller | Path | Purpose |
|------------|------|---------|
| [System](#system) | `/system` | Status, metrics, state |
| [Actions](#actions) | `/actions` | Kill switch, resume, rebalance |
| [Orders](#orders) | `/orders` | Submit orders, view positions |
| [Market](#market) | `/market` | Historical price data |
| [Signals](#signals) | `/signals` | Recent trading signals |

---

## Health Check

### GET `/health`

Check if the API is running.

**Response:**

```json
{
  "status": "ok"
}
```

---

## System

### GET `/system/status`

Get high-level system status.

**Response:**

```json
{
  "status": "Online",
  "active_agents": 8,
  "version": "2.0.0-alpha"
}
```

---

### GET `/system/metrics`

Get current system performance metrics.

**Response:**

```json
{
  "pnl_24h": 12450.00,
  "pnl_trend_pct": 2.4,
  "system_load_pct": 42.0,
  "open_positions": 14
}
```

---

### GET `/system/state/current`

Get the latest agent state for the Terminal UI.

**Response:**

```json
{
  "timestamp": "2025-12-21T12:00:00.000000",
  "status": "ACTIVE",
  "market": {
    "symbol": "SPY",
    "price": 450.32,
    "alpha": 2.8,
    "regime": "Gaussian",
    "velocity": 0.002,
    "acceleration": 0.0001
  },
  "portfolio": {
    "nav": 100000.00,
    "cash": 85000.00,
    "daily_pnl": 1250.00,
    "max_drawdown": -0.05
  },
  "signal": {
    "side": "BUY",
    "confidence": 0.85,
    "reasoning": "Momentum aligned with forecast"
  },
  "governance": {
    "approved_size": 15000.00
  },
  "logs": [
    "[ANALYST]: Signal generated...",
    "[RISK]: Position approved..."
  ]
}
```

**Error Response (no state available):**

```json
{
  "error": "No state available",
  "status": "offline"
}
```

---

### GET `/system/state/history`

Get recent state snapshots.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Number of snapshots to return |

**Response:**

```json
{
  "count": 10,
  "snapshots": [
    {
      "id": 123,
      "timestamp": "2025-12-21T12:00:00.000000",
      "alpha": 2.8,
      "regime": "Gaussian",
      "signal_side": "BUY",
      "approved_size": 15000.00,
      "status": "ACTIVE"
    }
  ]
}
```

---

### GET `/system/metrics/agents`

Get performance metrics for all agents.

**Response:**

```json
{
  "agents": [
    {
      "name": "AnalystAgent",
      "latency_ms": 1500,
      "success_rate": 0.98,
      "last_run": "2025-12-21T12:00:00.000000"
    }
  ]
}
```

---

### GET `/system/metrics/models`

Get model performance metrics (FinBERT, Gemma2, Chronos).

**Response:**

```json
{
  "models": [
    {
      "name": "chronos",
      "latency_ms": 120,
      "predictions": 500,
      "last_inference": "2025-12-21T12:00:00.000000"
    }
  ]
}
```

---

### GET `/system/status/physics`

Get latest physics metrics for dashboard.

**Response:**

```json
{
  "alpha": 2.8,
  "velocity": 0.002,
  "acceleration": 0.0001,
  "regime": "Gaussian",
  "timestamp": "2025-12-21T12:00:00.000000"
}
```

**Default Response (no history):**

```json
{
  "alpha": 3.0,
  "velocity": 0.0,
  "acceleration": 0.0,
  "regime": "Unknown",
  "timestamp": null
}
```

---

## Actions

### POST `/actions/halt`

Trigger emergency system halt (Kill Switch).

**Response:**

```json
{
  "success": true,
  "message": "🛑 Kill Switch Engaged. Agent Loop Paused."
}
```

---

### POST `/actions/resume`

Resume system from emergency halt.

**Response:**

```json
{
  "success": true,
  "message": "✅ System Resumed. Agent Loop Active."
}
```

---

### POST `/actions/rebalance`

Trigger portfolio rebalancing.

**Response:**

```json
{
  "success": true,
  "message": "Rebalance Started"
}
```

---

### POST `/actions/export-logs`

Trigger log export to S3.

**Response:**

```json
{
  "success": true,
  "message": "Logs Exported to S3"
}
```

---

## Orders

### POST `/orders/submit`

Submit a new order to Alpaca.

**Request Body:**

```json
{
  "symbol": "SPY",
  "qty": 10.0,
  "side": "buy",
  "type": "market",
  "limit_price": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `symbol` | string | ✅ | Ticker symbol |
| `qty` | float | ✅ | Quantity |
| `side` | string | ✅ | `"buy"` or `"sell"` |
| `type` | string | ❌ | `"market"` (default) or `"limit"` |
| `limit_price` | float | ❌ | Required if type is `"limit"` |

**Success Response:**

```json
{
  "success": true,
  "order_id": "abc123-def456",
  "message": "Order submitted successfully"
}
```

**Error Response:**

```json
{
  "success": false,
  "order_id": null,
  "message": "Insufficient buying power"
}
```

---

### GET `/orders/positions`

Get current open positions from Alpaca.

**Response:**

```json
[
  {
    "symbol": "SPY",
    "qty": 10.0,
    "avg_entry_price": 450.00,
    "current_price": 452.50,
    "unrealized_pl": 25.00,
    "unrealized_plpc": 0.0056,
    "market_value": 4525.00
  }
]
```

**Empty Response (no positions):**

```json
[]
```

---

## Market

### GET `/market/history/{symbol}`

Fetch historical bars for a symbol. Used for chart population.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `symbol` | string | Ticker symbol (e.g., `SPY`) |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 100 | Number of bars to return |

**Response:**

```json
[
  {
    "time": 1703174400,
    "open": 450.00,
    "high": 451.50,
    "low": 449.50,
    "close": 451.00,
    "volume": 1234567
  }
]
```

**Error Response:**

```json
[]
```

---

## Signals

### GET `/signals/`

Get recent trading signals.

**Response:**

```json
[
  {
    "time": "10:42:05",
    "symbol": "BTC-PERP",
    "action": "LONG",
    "confidence": "92%"
  },
  {
    "time": "10:41:12",
    "symbol": "ETH-PERP",
    "action": "SHORT",
    "confidence": "88%"
  }
]
```

---

## Error Handling

All endpoints return standard HTTP status codes:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Rate Limits

No rate limits enforced (internal API).

---

## CORS

CORS is enabled for all origins:

```python
cors_config = CORSConfig(
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

---

## Related

- [WebSocket Protocol](./websocket-protocol.md)
- [Redis Protocol](./redis-protocol.md)

---

*Last Updated: 2025-12-21*

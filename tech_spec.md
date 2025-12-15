# CC-V2 Technical Specification v1.0

## 1. System Architecture
The system follows a Hexagonal Architecture (Ports & Adapters) pattern, centered around the **Cognitive Engine**.

### Layers:
1.  **Frontend (UI)**: React 19 + Vite dashboard for observability. Talks *only* to the BFF.
2.  **BFF (Edge)**: Node.js service managing authentication, rate limiting, and request aggregation.
3.  **Engine (Core)**: Python/Litestar service hosting the LangGraph agents.
4.  **Persistence**: TimescaleDB (Time-series & Vector Store).
5.  **Infrastructure**: Docker Compose orchestration.

## 2. API Specifications

### Risk & Physics
*   **Protocol**: Bayesian Expected Shortfall (BES) + Hill Estimator.
*   **Veto Logic**: If $\alpha \le 2.0$, Risk Allocation = 0.

### Trade Autopsy
**Endpoint**: `GET /api/v1/journal/trace/{id}`
**Description**: Retrieve the full cognitive reasoning chain for a specific decision.

**Response Schema (JSON)**:
```json
{
  "trace_id": "uuid",
  "symbol": "BTC/USD",
  "timestamp": "iso-8601",
  "final_decision": "BUY",
  "risk_score": 0.12,
  "sentiment_triad": {
    "bullish_score": 0.85,
    "bearish_score": 0.10,
    "neutral_score": 0.05
  },
  "agent_debate": {
    "round_1": {
      "analyst": "Strong momentum detected on 4H chart. FracDiff series stationary.",
      "macro": "Yields are spiking. I advise caution. Vetoing leverage.",
      "risk": "Hill Alpha is 2.4. Allowed, but reduce size."
    },
    "round_2": {
      "execution": "Liquidity is thin. Suggest TWAP entry."
    }
  },
  "physics_metrics": {
    "alpha": 2.4,
    "bes_95": 0.045,
    "kalman_acceleration": 0.0012
  }
}
```

## 3. Data Pipeline
*   **Ingestion**: Tiingo (Websocket + REST).
*   **Preprocessing**: Fractional Differentiation (Standard `d=0.4` unless optimized).
*   **Storage**: TimescaleDB Hypertables for ticks; pgvector for agent embeddings.

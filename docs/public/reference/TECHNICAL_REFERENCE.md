# Curiosity Cottage Technical Reference Manual

**Version**: 3.1
**Date**: December 2025
**Status**: Live / Production Ready

## 1. System Architecture

The **Curiosity Cottage Quant Engine (CC-V2)** is a hybrid-metal autonomous trading system designed for high-frequency cognitive decision making. It fuses quantitative finance (Physics/Kalman Filters) with large language model reasoning (Ollama/Gemma).

### High-Level Diagram

```mermaid
graph TD
    User[Trader] -->|View| FE[Frontend (Glass Cockpit)]
    FE -->|WebSocket| Stream[BacktestStream / BrainStream]
    FE -->|REST| API[API Server (Litestar)]
    
    API -->|Control| Controller[BacktestController]
    
    subgraph "The Cognitive Engine"
        Macro[Macro Node] -->|Candidates| Analyst[Analyst Node]
        Analyst -->|Signal| Risk[Taleb (Risk Node)]
        Risk -->|Verdict| Simons[Simons Node]
    end
    
    subgraph "The Brain (gRPC)"
        Brain[BrainService]
        Chronos[Chronos-Bolt (MPS)]
        FinBERT[FinBERT (ONNX)]
        Brain --> Chronos
        Brain --> FinBERT
    end
    
    subgraph "The Shannon Channel"
        Engine[BacktestEngine] -->|Pub Progress| Redis[(Dragonfly)]
        Redis -->|Sub| Stream
    end
    
    Controller -->|Spawn| Engine
    Analyst -->|RPC| Brain
    Simons -->|Execute| AlpacaAPI
    Simons -->|Log| QuestDB
    
    subgraph "Observability"
        OTEL[OTEL Collector] -->|Export| GrafanaCloud
    end
```

---

## 2. Core Flows: "The Consciousness Loop"

The system runs on an event-driven loop, managed by `app/agent/loop.py`.

### 1. Macro Awareness (`app/agent/nodes/macro.py`)

- **Trigger**: Interval or Manual (via `MarketScanner.get_active_universe`).
- **Input**: None.
- **Process**: Scans the market for "Hot" assets (Vol > $20M, Px > $5, Change > 1.5%).
- **Output**: A prioritized list of `symbol` candidates.

### 2. Deep Analysis (`app/agent/nodes/analyst.py`)

- **Input**: Candidate Symbol.
- **Process**:
  1. **Physics**: Calculates Velocity/Acceleration via Kalman Filter (`PhysicsService`).
  2. **Memory**: Retrieves past performance for this symbol (`MemoryService`).
  3. **Reasoning**: Two-stage LLM think-tank:
     - *Quant*: Analyzes numerical trends.
     - *Fundamental*: Analyzes news sentiment (FinBERT via ONNX Runtime).
- **Output**: A `Signal` (BUY/SELL/HOLD), Confidence (0-1), and `Reasoning` string.

### 3. The Risk Tournament (`app/agent/nodes/risk.py`)

- **Input**: Signal + AgentState.
- **Process**: "The Iron Gate"
  1. **Circuit Breaker**: Checks 5% daily drawdown limit.
  2. **Physics Veto**: Rejects trade if Velocity is 0 (Frozen) or Alpha < 1.5 (Chaos).
  3. **Sizing**: Calculates Bayesian Expected Shortfall (BES) Fraction * Alpha Scalar.
- **Output**: `TOURNAMENT_VERDICT` (Approved Size or Rejection).

### 4. Execution (`app/agent/nodes/simons.py`)

- **Input**: Verdict (Approved Size).
- **Process**:
  - Validates cash/margin.
  - Routes order to Alpaca via `MarketService`.
  - Logs execution to `QuestDB` (trades table).
- **Role**: **The Quant** (Simons Persona).
- **Output**: Order Confirmation / fill data.

### 5. Broadcast (`app/api/routes/websocket.py`)

- **Event**: `NODE_UPDATE` and `TOURNAMENT_VERDICT`.
- **Action**: Pushed to WebSocket (`ws://host/api/ws/brain`) for Frontend visualization.

---

## 3. Services & Code Modules

### Reference Guide by Directory

#### `app/services/`

The domain logic layer. Agents do not talk to APIs directly; they talk to Services.

- **`market.py`**: **The Library of Hypatia**.
  - *Role*: Unified Data Access Layer (DAL).
  - *Components*:
    - **The Shannon Channel** (Redis/Stream).
    - **The Scrolls of Herodotus** (QuestDB/History).
  - *Key Method*: `get_price(symbol)` - Tries Alpaca -> Tiingo -> Finnhub -> YFinance.
  
- **`physics.py`**: **The Physicist**.
  - *Role*: Heavy math & State estimation.
  - *Key Method*: `calculate_physics_state(df)` - Runs Kalman Filter + Hill Estimator (Alpha).
  - *Key Code*: `KinematicKalmanFilter` class implementation.
  - *feature*: **Adaptive Noise Scaling** (v3.3.1) - Scales `R` (Measurement Noise) by `(1+vol^2)` to resist Levy Flights.
  - *Reference*: `docs/00_CONSTITUTION/02_physics_v4.md`.

- **`forecast.py`**: **The Oracle** (New in v3.1).
  - *Role*: Time-series forecasting.
  - *Engine*: `amazon/chronos-bolt-small` (Pre-trained foundation model).
  - *Integration*: Uses HuggingFace Transformers + MPS acceleration.
  - *Logic*: `RelativityOperator` (v3.2) enforces trend harmony between 1m (Context) and 5m (Forecast).
  - *Output*: Probabilistic forecasts (P10, P50, P90).

- **`rag_forecast.py`**: **The Hippocampus** (New in v3.1).
  - *Role*: Retrieval Augmented Generation (Market Memory).
  - *Engine*: LanceDB (Vector Database).
  - *Process*: Search closest 64-day pattern -> Filter by `cutoff_timestamp` -> Weighted Average Outcome.

- **`backtest.py`**: **The Quantum Holodeck** (New in v3.1).
  - *Role*: Vectorized Time-Travel Simulator.
  - *Purpose*: Validates the Oracle & Hippocampus offline.
  - *Streaming*: **The Shannon Channel** (v0.12.0) - Publishes progress to Redis `backtest:{run_id}`.
  - *Key Method*: `run()` - Orchestrates the full simulation loop.

- **`brain_service.py`**: **The Brain** (New in v0.12.0).
  - *Role*: gRPC Host for AI Models.
  - *Contract*: `protos/brain.proto` (**The Rosetta Stone**).
  - *Methods*: `Forecast()` and `AnalyzeSentiment()`.

- **`state.py`**: **The Conscious Mind**.
  - *Role*: Global State Definition.
  - *Feature*: `CognitiveState` (v3.2) - Tracks `anxiety_score` and `regret_matrix`.
  - *Logic*: If `anxiety > 0.7`, Risk Node halves position sizing automatically.

- **`reasoning.py`**: **The Philosopher**.
  - *Role*: LLM Interaction.
  - *Key Method*: `analyze_signal()` - Prompts Ollama with structured context.
  - *Metrics*: Tracks token usage and inference latency for Telemetry.

- **`scanner.py`**: **The Scout**.
  - *Role*: Dynamic Universe Generation.
  - *Key Method*: `get_active_universe()` - Returns top 20 volatile tickers.

#### `app/adapters/`

The interface to the outside world.

- **`market.py`**: Unified `MarketAdapter` abstract base class.
- **`alpaca.py`, `tiingo.py`, `finnhub.py`**: Concrete implementations.
- **`llm.py`**: `OllamaAdapter` connecting to local LLM on port 11434.

#### `app/agent/nodes/`

The "Brains" of the operation.

- **`analyst.py`**:
  - *Hoisting*: Lifts critical data (`velocity`, `price`) to global state for downstream nodes.
- **`risk.py`**:
  - *Verdict*: Emits specific `TOURNAMENT_VERDICT` events for the frontend.

---

## 4. Frontend Architecture ("The Glass Cockpit")

Located in `frontend/`. React + Vite + TailwindCSS.

- **`App.tsx`**: The Root.
  - **Telemetry Gate**: Blocks render until `initTelemetry()` completes.
  - **Tabs**: Switcher for "Consciousness" vs "Operations".

- **`connection_manager.ts`**: **Telemetry Resilience** (v3.1.3).
  - *Role*: Hardened WebSocket Client.
  - *Features*:
    - **Exponential Backoff**: 1s -> 30s retry logic.
    - **Heartbeat**: Detects "Dead Air" (>10s silence) -> CRITICAL State.
  - *Integration*: `ProTerminal.tsx` uses this for visual "Red Alert" states.

---

## 5. Observability Pipeline

- **logs/traces** -> **OTEL Collector** (Docker, Port 4317/4318).
- **Collector** -> **Grafana Cloud** (Loki/Tempo/Prometheus).
- **Frontend RUM** -> **Grafana Faro** -> **Collector**.

All business metrics are prefixed with `cc.` (e.g., `cc.physics.alpha`, `cc.risk.vetoes`).

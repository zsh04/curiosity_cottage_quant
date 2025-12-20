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
    FE -->|WebSocket| API[API Server (Litestar)]
    FE -->|REST| API
    
    API -->|Control| Engine[Agent Graph (LangGraph)]
    
    subgraph "The Cognitive Engine"
        Macro[Macro Node] -->|Candidates| Analyst[Analyst Node]
        Analyst -->|Signal| Risk[Risk Node]
        Risk -->|Verdict| Execution[Execution Node]
    end
    
    subgraph "Service Layer"
        Market[Market Service]
        Physics[Physics Service]
        Reasoning[Reasoning Service]
        Memory[Memory Service]
    end
    
    Engine --> ServiceLayer
    
    Market -->|Failover| Adapter[Market Adapters]
    Adapter --> Alpaca & Tiingo & Finnhub
    
    Physics -->|Calc| Chronos[Chronos-Bolt (Time Series)]
    Reasoning -->|Inference| Ollama[Ollama (Gemma:2b)]
    
    Execution -->|Trade| AlpacaAPI
    
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
     - *Fundamental*: Analyzes news sentiment (FinBERT).
- **Output**: A `Signal` (BUY/SELL/HOLD), Confidence (0-1), and `Reasoning` string.

### 3. The Risk Tournament (`app/agent/nodes/risk.py`)

- **Input**: Signal + AgentState.
- **Process**: "The Iron Gate"
  1. **Circuit Breaker**: Checks 5% daily drawdown limit.
  2. **Physics Veto**: Rejects trade if Velocity is 0 (Frozen) or Alpha < 1.5 (Chaos).
  3. **Sizing**: Calculates Kelly Fraction * Volatility Adjustment.
- **Output**: `TOURNAMENT_VERDICT` (Approved Size or Rejection).

### 4. Execution (`app/agent/nodes/execution.py`)

- **Input**: Verdict (Approved Size).
- **Process**:
  - Validates cash/margin.
  - Routes order to Alpaca via `MarketService`.
- **Output**: Order Confirmation / fill data.

### 5. Broadcast (`app/api/routes/websocket.py`)

- **Event**: `NODE_UPDATE` and `TOURNAMENT_VERDICT`.
- **Action**: Pushed to WebSocket (`ws://host/api/ws/brain`) for Frontend visualization.

---

## 3. Services & Code Modules

### Reference Guide by Directory

#### `app/services/`

The domain logic layer. Agents do not talk to APIs directly; they talk to Services.

- **`market.py`**: **The Librarian**.
  - *Role*: Facade for all market data.
  - *Key Method*: `get_price(symbol)` - Tries Alpaca -> Tiingo -> Finnhub -> YFinance.
  
- **`physics.py`**: **The Physicist**.
  - *Role*: Heavy math & State estimation.
  - *Key Method*: `calculate_physics_state(df)` - Runs Kalman Filter + Hill Estimator (Alpha).
  - *Key Code*: `KinematicKalmanFilter` class implementation.

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

- **`components/DebateConsole.jsx`**: The Visualization.
  - **WebSocket**: Connects to `ws://localhost:8000/api/ws/brain`.
  - **State**: Uses `useWebSocket` (native).
  - **UI**:
    - *Analysts*: Cards with Sentiment/Physics indicators.
    - *Arena*: Auto-scrolling text log of "Thoughts".
    - *Verdict*: Dynamic status dashboard.

---

## 5. Observability Pipeline

- **logs/traces** -> **OTEL Collector** (Docker, Port 4317/4318).
- **Collector** -> **Grafana Cloud** (Loki/Tempo/Prometheus).
- **Frontend RUM** -> **Grafana Faro** -> **Collector**.

All business metrics are prefixed with `cc.` (e.g., `cc.physics.alpha`, `cc.risk.vetoes`).

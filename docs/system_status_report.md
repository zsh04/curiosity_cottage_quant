# System Status Report: Curiosity Cottage Quant
**Date:** December 14, 2025

## Executive Summary
The Curiosity Cottage Quant system has evolved into a sophisticated, agentic trading platform driven by cognitive architecture and physics-based risk management. The core infrastructure is now operational, featuring a multi-agent decision loop, rigorous event-driven backtesting standards, and a "Physics Veto" mechanism to prevent catastrophic losses.

## Tech Stack Decisions
We have standardized on a high-performance, modern stack to support real-time data processing and cognitive agency:

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | **Litestar** (Python) | Chosen for its superior performance over FastAPI, native support for async/await, and cleaner dependency injection, critical for our high-throughput trading engine. |
| **Frontend** | **React + Vite** (TypeScript) | Provides a responsive, type-safe Control Center. Vite ensures rapid development cycles, and React offers the component ecosystem needed for complex dashboards. |
| **Database** | **TimescaleDB** | An extension of PostgreSQL optimized for time-series data. It handles our tick-level market data and "State Estimates" history with compression and efficiency. |
| **AI Orchestration** | **LangGraph** | Enables the creation of stateful, multi-agent workflows (Macro -> Analyst -> Execution) with cyclic graph capabilities, superior to linear chains. |
| **Local LLMs** | **Ollama** | Allows us to run quantized models (like Gemma 2) locally for privacy and cost-efficiency within the "Analyst Agent" workflow. |
| **Data Providers** | **Tiingo** (Primary), **Finnhub** (Backup) | Tiingo provides high-fidelity institutional data. Finnhub serves as a redundant failover for news and price feeds to ensure system resilience. |
| **Infrastructure** | **Docker Compose** | Ensures reproducible environments for all services, including the database and AI model servers. |

## Core Components Implemented

### 1. Cognitive Agent Architecture (LangGraph)
We have successfully implemented a hierarchical agent system using **LangGraph**:
- **Macro Agent**: Analyzes broad market conditions and regime shifts.
- **Analyst Agent**: Conducts deep-dive technical and fundamental analysis on specific assets.
- **Execution Agent**: Optimizes trade entry/exit execution.
- **Orchestration**: These agents coordinate in a structured graph, passing state and context to form a cohesive decision-making pipeline.

### 2. Physics-Based Risk Management ("The Physics Veto")
A novel risk management layer has been integrated to detect and reject trades in dangerous regimes:
- **Kinematic Kalman Filter**: A 3-state filter (Position, Velocity, Acceleration) estimates the "kinematics" of price action.
- **Heavy Tail Detection**: A `HeavyTailEstimator` calculates the Power Law exponent (Alpha) to identify infinite variance regimes.
- **Risk Guardian**: A distinct logic layer that "vetoes" any trade signals if the market physics suggest high probability of ruin (e.g., extreme acceleration or unbounded variance).

### 3. Advanced Capital Allocation
- **Fractional Kelly Criterion**: Adapted for continuous probability streams, maximizing geometric growth while maintaining a safety buffer.
- **Shared Logic**: The sizing logic (`infer_probabilistic_success`) is unified across both the live execution router and the backtesting engine to ensure "what you test is what you trade."

### 4. Data Pipeline & Processing
- **Tiingo Integration**: Implemented as the primary data source for historical bars, live quotes, and news.
- **Failover Redundancy**: Automatic failover to Finnhub for news data if primary feeds are disrupted.
- **Fractional Differentiation (FracDiff)**: Protocol defined for preprocessing time-series data to achieve stationarity without erasing memory (unlike standard differencing).

### 5. Control Center & Operations
- **Backend**: A Litestar-based backend connects the frontend dashboard to the trading engine.
- **Operational Runbook**: A formal `runbook.md` and emergency scripts (e.g., `flatten_all.py`) establish clear procedures for system monitoring and crisis management.
- **Dockerized Infrastructure**: Services (TimescaleDB, Ollama for local LLMs) are containerized for consistent deployment.

## Validation & Backtesting Standards
We have codified a rigorous **"No Cheating"** protocol for strategy validation:
- **Event-Driven Only**: No vectorized backtests; all strategies must simulate latency (100ms), variable slippage, and partial fills.
- **Purged & Embargoed CV**: Training data is rigorously separated from test data with "embargo" periods to prevent leakage from serial correlation.

## Next Steps
- **Finalize Control Center UI**: Complete the wiring of the frontend dashboard to the new backend endpoints.
- **Testing**: Continue rigorous event-driven backtesting of the implemented agents.
- **FracDiff Implementation**: Fully operationalize the Fractional Differentiation data loaders for all models.

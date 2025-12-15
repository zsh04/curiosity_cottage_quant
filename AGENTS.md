# Autonomous Agent Protocol (Internal Only)

## 1. Operational Mandate
The goal of this system is to generate consistent, uncorrelated Alpha through **Regime-Aware Swing Trading**.
* **Capital Constraint:** System must optimize for **Micro-Account ($500 Seed)** survival.
    * **Execution:** Must support fractional shares.
    * **Drawdown Limit:** Hard stop at 2% NAV loss per day.
* **Target Metric:** Sharpe Ratio > 1.5.
* **Time Horizon:** 4 Hours - 5 Days (Swing).

## 2. The Cognitive Architecture
We employ a **Federated Agent Model** orchestrated via LangGraph:
1.  **Analyst (The Engine):** Ingests multi-modal data (Price, News, Macro) to generate Probabilistic Signals.
2.  **Macro (The Context):** Monitors Global Liquidity (Yields, VIX, Correlations). Has **VETO** power over the Analyst.
3.  **Risk (The Governance):** Enforces the **CCQP (Curiosity Cottage Quantitative Protocol)**. Calculates sizing based on **Bayesian Expected Shortfall (BES)** and Physics Veto.
4.  **Execution (The Action):** Manages order lifecycle and slippage optimization.

## 3. The "Physics" Constraints
* **The Alpha Rule:** Trading is mathematically forbidden if the Tail Index $\alpha \le 2.0$ (Infinite Variance Regime).
* **The Latency Rule:** Cognitive Agents (LLMs) operate on the *Strategy Plane* (Hourly). Execution Algorithms operate on the *Trade Plane* (Real-time).

## 4. Engineering Standards
* **Architecture:** Hexagonal (Ports & Adapters).
* **Typing:** Strict Python 3.12+ type hinting (Pydantic DTOs).
* **Persistence:** All agent reasoning must be logged to PGVector for auditability.

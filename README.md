# Project Ezekiel: The Micro-Sovereign

![System Health](https://img.shields.io/badge/Law%20Zero-ENFORCED-brightgreen)
![Capital Constraint](https://img.shields.io/badge/Seed%20Capital-%24500-red)
![Architecture](https://img.shields.io/badge/Architecture-Bicameral%20Mind-blue)
![Python](https://img.shields.io/badge/Python-3.11-yellow)

> **"Constraint Breeds Creativity."**

---

## 🏛️ System Overview

**Project Ezekiel** is a sovereign, biological algorithmic trading system designed to solve the **Micro-Capital Paradox**: *How to generate Alpha with only $500, running on local silicon, without the crutch of leverage or high-frequency data.*

Unlike traditional "Black Box" AI that blindly predicts price, Ezekiel is a **Physics Engine**. It treats the market as a physical system governed by Kinematics (Momentum), Thermodynamics (Entropy), and Gravity (Mean Reversion).

### The Constraints (The Forge)

The system is hardened by three non-negotiable boundary conditions:

1. **The Micro-Seed:** $500 Starting Capital. Zero tolerance for drawdown.
2. **The Silicon Sovereign:** Runs locally on Apple Silicon (M-Series). No Cloud dependencies.
3. **The Regulatory Physics:** Cash Account Only. Respects **T+1 Settlement** and **Temporal Rationing** to evade Pattern Day Trader (PDT) locks.

---

## 🧠 The Architecture: The Bicameral Mind

The system separates cognitive functions into two decoupled organs to ensure speed without sacrificing safety.

### 1. The Brain (Global Inference)

* **Role:** $O(1)$ Probability Forecasting.
* **Engine:** **Chronos** (Time-Series Transformer).
* **Output:** The 10-Quantile Wave Function ($\Quant_t$)—predicting the *shape* of uncertainty, not just the price.

### 2. The Body (Local Execution)

* **Role:** $O(N)$ Micro-Structure Analysis.
* **Engine:** **Simons** (Execution Agent).
* **Output:** Performs local Order Book scans to calculate **Predatory Slippage** and place limit orders.

### 3. The Council (Vector Logic)

A deterministic logic layer where Agents exchange strict **mathematical vectors**. There is no voting; there is only Physics.

| Agent | Role | Vector Contract |
| :--- | :--- | :--- |
| **Feynman** | The Physicist | Outputs **Mass, Momentum, Entropy, Jerk**. |
| **Soros** | The Feeler | Outputs **Reflexivity Index** (Self-Impact detection). |
| **Boyd** | The Strategist | Fuses Physics + Reflexivity + Chaos into **Urgency**. |
| **Nash** | The Allocator | Enforces **Temporal Rationing** (T+1 Budgeting). |
| **Taleb** | The Guardian | Enforces **Skew Limits** (Crash Protection). |
| **Hypatia** | The Librarian | Manages Data & applies the **Sparse Data Scalar** (IEX Correction). |
| **Shannon** | The Signalman | Enforces **Law Zero** (Hardware Health). |

---

## 📡 The Data Ecology

We utilize a hybrid array of data sources to ensure redundancy and depth.

| Category | Sources | Role |
| :--- | :--- | :--- |
| **Primary Feed** | **Alpaca** (IEX) | Real-time Tick Data & Order Execution. |
| **Research/History** | **Tiingo**, **yFinance** | Adjusted OHLCV history & Corporate Actions. |
| **Sentiment/News** | **NewsAPI.org**, **Finviz** | NLP ingestion for Soros's Reflexivity Index. |
| **Backup Layers** | **TwelveData**, **MarketStack**, **AlphaVantage** | "Reserve Parachutes" (Configurable Failover). |

---

## ⚡ Technology Stack

| Component | Technology | Role |
|-----------|------------|------|
| **Core** | Python 3.11 | The Metal (AsyncIO / Uvloop) |
| **Bus** | Dragonfly (Redis) | **The Hot Memory** (Signal/Health Bus) |
| **History**| QuestDB | **The Cold Storage** (ILP High-Speed Ingest) |
| **Inference**| PyTorch (MPS) | Hardware-Accelerated Tensors on Apple Silicon |
| **API** | Litestar | High-Performance REST Interface |

---

## ♟️ Active Strategies

The system does not rely on a single algorithm. It uses an ensemble of Logic and Chaos.

### The Physics Core

* **KalmanMomentum:** Uses Kinematic State Estimation to track velocity ($v$).
* **FractalBreakout:** Uses Fractional Differentiation ($d$) to detect regime shifts while preserving memory.
* **BollingerReversion:** Exploits mean reversion when Price deviates $>2\sigma$ from the center of gravity.

### The Chaos Agent

* **MoonPhase:** A deterministic "Dithering Agent."
  * *Role:* Injects a small entropy signal (correlated with lunar cycles) into the decision vector.
  * *Implementation:* `MoonPhase_V1` (New Moon = Buy, Full Moon = Sell).

### The Neural Agent

* **EchoState (LSTM):** A Reservoir Computing Network with Recursive Least Squares ($O(1)$).
  * *Role:* Non-linear pattern recognition without the $O(N^3)$ training cost of Transformers.
  * *Implementation:* `EchoState_RLS_V2`.

### The Quantum Agent

* **QuantumHarmonic:** Models price as displacement in a potential well.
  * *Role:* Detects "Energy Violations" (Mean Reversion) using harmonic oscillator physics.
  * *Implementation:* `QuantumHarmonic_V1`.

---

## 📜 The Immutable Laws

The Council is bound by five hard-coded laws that override all AI predictions.

1. **Law Zero (Integrity):** If Hardware Health < 99.9% (Latency/Jitter), **HALT**.
2. **Law I (Momentum):** Price moves without Volume (Mass) are hallucinations ("Ghost Momentum").
3. **Law II (Gravity):** Price cannot escape the Median Forecast ($q_{50}$) indefinitely.
4. **Law III (Entropy):** If Volatility expands beyond the **Hypatia Limit** (Adaptive), the system is blind. **HALT**.
5. **Law V (Conservation):** A 2% intraday drawdown triggers a hard kill switch.

---

## 🛡️ Testing & Verification

The system employs **Adversarial Reflexivity Testing** to ensure it survives in a hostile environment.

* **The Soros Loop:** We simulate a scenario where the bot is the *only* buyer. If it chases its own price, the test fails.
* **The PDT Trap:** We simulate a 100% allocation at 9:30 AM. **Nash** must veto all subsequent trades due to lack of T+1 Buying Power.

---

## 🚀 Quick Start

### 1. Configuration

Set your `DATA_PROVIDER` in `.env`.

```bash
# Options: "alpaca" (Default), "twelvedata", "alphavantage"
DATA_PROVIDER=alpaca
LIVE_TRADING_ENABLED=False

# Curiosity Cottage Quant

### The Shannon Channel (v0.12.0)

> **"Trust Physics, Not Emotion."**

---

## 🏛️ System Overview

**Curiosity Cottage Quant (CCQ)** is an autonomous, physics-driven trading system built on the **Hybrid Metal Architecture**. It is not just a backtester or a bot; it is a **cybernetic organism** managed by a "Council" of AI agents that debate, reason, and execute trades under strict risk constraints.

### 2. The Council (Cognitive Stack)

The system is governed by a "Bicameral Mind" of specialized agents:

- **Soros (The Philosopher):** Scans the global universe for regime changes and volatility.
- **Boyd (The Strategist):** Executes the OODA Loop to orient and decide on tactics.
- **Taleb (The Guardian):** Enforces risk limits and "black swan" protection.
- **Simons (The Executioner):** Handles high-precision order slicing and routing.

### ⚛️ The Physics Engine (Risk Core)

A deterministic "Veto Layer" that overrides AI consensus if physical laws of the market are violated.

- **Law I: Inertia** (Adaptive Kinematic Kalman Filter)
  *Markets have momentum; a trend in motion tends to stay in motion (Newton's 1st).*
- **Law II: Entropy** (Hill Estimator & Hurst Exponent)
  *Markets tend towards disorder; infinite variance (Heavy Tails) violates Gaussian models.*
- **Law III: Conservation of Capital** (Bayesian Expected Shortfall)
  *Energy (Capital) cannot be created from nothing; it must be preserved against Ruin.*

---

## ⚡ Technology Stack

| Component | Technology | Role |
|-----------|------------|------|
| **Core** | Python 3.11 | The Metal (AsyncIO) |
| **Stream** | Redis (Dragonfly) | **The Shannon Channel** (Real-time Telemetry) |
| **Brain** | gRPC (Protobufs) | **The Rosetta Stone** (Strict Contracts) |
| **Memory** | LanceDB | Semantic Search / Embeddings |
| **History**| QuestDB | **The Scrolls of Herodotus** (Tick Data) |
| **Neural** | ONNX + MPS | Hardware-Accelerated Inference |
| **API** | Litestar | High-Performance REST Interface |

---

## 📚 Documentation

The knowledge base is organized according to the **Diátaxis** framework.

### 🟢 For Everyone (Public)

*Start here to understand how to use and deploy the system.*

- **[Quickstart Guide](docs/public/tutorials/01-quickstart.md)** — Launch the system in 10 minutes.
- **[How-To Guides](docs/public/how-to/)** — Add strategies, run backtests, or deploy.
- **[System Architecture](docs/public/reference/architecture/stack.md)** — Diagrams & Stack details.
- **[API Reference](docs/public/reference/api/rest-endpoints.md)** — REST interactions.

---

## ⚖️ Governance

This project is run as a **Directive-Driven** organization.

- **[GOVERNANCE.md](GOVERNANCE.md)** — The Constitution & Code of Conduct.
- **[PROJECT_MANAGEMENT.md](PROJECT_MANAGEMENT.md)** — Directive Workflow & Traceability.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Style Guide & PR Rules.

---

## 🚀 Quick Start

```bash
# 1. Install Dependencies
python3.11 -m pip install -r requirements.txt

# 2. Run the Engine
uvicorn app.main:app --reload

# 3. Access the Neural Stream
# http://localhost:8000/docs
```

---

*Copyright © 2025 Curiosity Cottage. All Rights Reserved.*

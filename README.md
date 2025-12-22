# Curiosity Cottage Quant

### The Ezekiel Operating System (v0.12.0)

> **"Trust Physics, Not Emotion."**

---

## 🏛️ System Overview

**Curiosity Cottage Quant (CCQ)** is an autonomous, physics-driven trading system built on the **Ezekiel Protocol**. It is not just a backtester or a bot; it is a **cybernetic organism** managed by a "Council" of AI agents that debate, reason, and execute trades under strict risk constraints.

### 🧠 The Council (Decision Engine)

- **The Oracle:** Unified Forecasting Engine (Chronos-Bolt + RAF Memory).
- **The Analyst:** Pattern recognition & sentiment analysis (FinBERT/ONNX).
- **The Skeptic:** Devil's advocate & risk challenger.
- **The Quant:** Statistical arbitrage & math checks (Chronos-Bolt/MPS).
- **The Executioner:** Order routing & state management.

### ⚛️ The Physics Engine (Risk Core)

A deterministic "Veto Layer" that overrides AI consensus if physical laws of the market are violated.

- **Law I: Conservation of Capital** (Kelly Criterion)
- **Law II: Entropy Management** (Hill Estimator & Tail Risk)
- **Law III: Kinematics** (Kalman Filter Velocity/Acceleration)

---

## ⚡ Technology Stack

| Component | Technology | Role |
|-----------|------------|------|
| **Core** | Python 3.11 | The Metal (AsyncIO) |
| **Memory** | LanceDB | Semantic Search / Embeddings |
| **Time-Series** | QuestDB | High-Frequency Tick Data |
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

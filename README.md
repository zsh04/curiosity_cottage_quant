# CC-V2 Quant Engine

Curiosity Cottage V2 Autonomous Trading System.

## Features

- **Consciousness Stream**: Real-time WebSocket feed of AI reasoning (`/api/ws/brain`).
- **Glass Cockpit**: React-based Command Center (`frontend/`) featuring:
  - **Debate Console**: Live visualization of Analyst/Risk debates.
  - **Pro Terminal**: Operational metrics and system controls.
- **Hybrid Core**: Python 3.11 Engine.
- **Neural Standardization**:
  - **Sentiment**: ONNX Runtime (FinBERT) - ~30ms latency.
  - **Forecast**: Chronos-Bolt (MPS) - Bfloat16 accelerated.

## Quick Start

1. **Backend**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. **Frontend**: `cd frontend && npm run dev`
3. **Access**: Open `http://localhost:3000`

See `AGENTS.md` for the internal protocol.

See `docs/00_CONSTITUTION/02_physics_v4.md` for the proprietary logic.

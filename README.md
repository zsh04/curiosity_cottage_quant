# CC-V2 Quant Engine

Curiosity Cottage V2 Autonomous Trading System.

## Features

- **Consciousness Stream**: Real-time WebSocket feed of AI reasoning (`/api/ws/brain`).
- **Glass Cockpit**: React-based Command Center (`frontend/`) featuring:
  - **Debate Console**: Live visualization of Analyst/Risk debates.
  - **Pro Terminal**: Operational metrics and system controls.
- **Hybrid Core**: Python 3.12 Engine with LangGraph Agents.

## Quick Start

1. **Backend**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. **Frontend**: `cd frontend && npm run dev`
3. **Access**: Open `http://localhost:3000`

See `AGENTS.md` for the internal protocol.

See `docs/protocol/mathematical-constitution.md` for the proprietary logic.

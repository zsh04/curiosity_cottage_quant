# Control Center UI Documentation

## Overview

The **Control Center** is the primary interface for monitoring the Curiosity Cottage Quant system. It provides real-time visualization of trading performance, agent status, and system health.

## Architecture

- **Framework**: React 18 + Vite (TypeScript)
- **Styling**: TailwindCSS (Cyberpunk Theme: Slate-950/Emerald-500)
- **Routing**: Tabbed Interface (No external router)
- **Data Layer**: Native WebSocket (`/api/ws/brain`) + REST
- **Telemetry**: Grafana Faro (RUM) initialized on startup

## Components

### 1. Consciousness Stream ("Debate Console")

The primary interface for visualizing the AI's internal reasoning loop.

- **Analysts Panel**: Left sidebar showing active tickers, sentiment gauge, and physics velocity vectors.
- **Arena**: Central log stream displaying raw `NODE_UPDATE` events ("Thoughts") in real-time.
- **Verdict**: Right panel with large visual indicators for Trade Decisions (BUY/HOLD/SHORT) and Risk Locks.

### 2. Operations ("Pro Terminal")

A high-density operational dashboard for system health.

- **Metrics**: Real-time display of Latency, Throughput, and Error rates.
- **Logs**: "Matrix-style" scrolling log of system events.

## Integration

- **Backend**: Connects via Proxy to `http://localhost:8000`
- **Observability**: Gated load ensures `initTelemetry()` completes before UI renders.

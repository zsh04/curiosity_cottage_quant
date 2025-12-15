# Control Center UI Documentation

## Overview
The **Control Center** is the primary interface for monitoring the Curiosity Cottage Quant system. It provides real-time visualization of trading performance, agent status, and system health.

## Architecture
- **Framework**: React 18 + Vite
- **Language**: JavaScript (JSX)
- **Styling**: Vanilla CSS with CSS Variables (HSL color space)
- **State Management**: Local React State (planned: Context/Redux for global state)
- **Backend Communication**: REST API via `/api` proxy to Python backend.

## Design System
The application uses a custom "Premium Dark Mode" design system defined in `src/index.css`.

### Key Variables
| Variable | Description |
|----------|-------------|
| `--color-primary` | Main brand color (hsl: 215, 90%, 60%) |
| `--color-bg` | Deep dark background (hsl: 220, 20%, 10%) |
| `--glass-panel` | Translucent background with blur for cards |

### Components

#### `Layout`
The main wrapper component providing the `Sidebar` and content area structure.

#### `Dashboard`
The landing page containing:
1. **Stats Grid**: High-level metrics (PnL, Active Agents).
2. **Market Activity**: Placeholder for chart visualizations.
3. **Recent Signals**: Log of recent system actions.
4. **Quick Actions**: Buttons for manual intervention (Halt, Rebalance).

## Development

### Setup
```bash
cd frontend
npm install
npm run dev
```

### Build
```bash
npm run build
```
Output is generated in `frontend/dist`.

# Tutorial: Get Started in 10 Minutes

**Time Required:** 10 minutes  
**Difficulty:** Beginner  
**Prerequisites:** Python 3.11+, Git, Redis

---

## What You'll Learn

By the end of this tutorial, you will:

- Clone and set up the Curiosity Cottage Quant engine
- Configure API keys and environment
- Start the trading engine in simulation mode
- View the real-time dashboard

---

## What You'll Build

A running instance of the Curiosity Cottage trading engine with:

- Real-time market data ingestion
- Physics-based regime detection
- AI-powered signal generation
- Live dashboard visualization

---

## Prerequisites

Before starting, ensure you have:

- [ ] Python 3.11 or higher installed
- [ ] Git installed
- [ ] Redis running locally (or Docker)
- [ ] Alpaca API keys (free tier works)

---

## Step 1: Clone the Repository

Open your terminal and clone the project:

```bash
git clone https://github.com/your-org/curiosity_cottage_quant.git
cd curiosity_cottage_quant
```

---

## Step 2: Create Virtual Environment

Create and activate a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

---

## Step 3: Install Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

> [!TIP]
> On Apple Silicon, use `requirements-metal.txt` for GPU acceleration:
>
> ```bash
> pip install -r requirements-metal.txt
> ```

---

## Step 4: Configure Environment

Copy the environment template:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# Required
ALPACA_API_KEY=your_alpaca_key
ALPACA_API_SECRET=your_alpaca_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Optional (for news sentiment)
TIINGO_API_KEY=your_tiingo_key

# Redis (default works for local)
REDIS_URL=redis://localhost:6379
```

> [!NOTE]
> You can get free Alpaca API keys at [alpaca.markets](https://alpaca.markets/).

---

## Step 5: Start Redis

If you have Docker:

```bash
docker-compose up -d redis
```

Or if Redis is installed locally:

```bash
redis-server
```

Verify Redis is running:

```bash
redis-cli ping
# Expected: PONG
```

---

## Step 6: Start the Engine

Run the trading engine:

```bash
python run.py
```

**Expected Output:**

```
2025-12-21 12:00:00 | ENGINE | INFO | Starting Curiosity Cottage Quant...
2025-12-21 12:00:01 | SIMONS | INFO | Chronos Neural Matrix Loaded.
2025-12-21 12:00:02 | SOROS  | INFO | Sentiment Engine (ONNX) Loaded.
2025-12-21 12:00:03 | ENGINE | INFO | ✅ Engine running at http://localhost:8000
```

---

## Step 7: Open the Dashboard

Open your browser and navigate to:

```
http://localhost:8000
```

You should see the ProTerminal interface with:

- Real-time candlestick chart
- Physics gauges (α, regime)
- Sentiment indicators
- Agent activity logs

---

## Step 8: Verify the System

Check system health via the API:

```bash
curl http://localhost:8000/api/health
```

**Expected Response:**

```json
{
  "status": "healthy",
  "components": {
    "redis": "connected",
    "chronos": "loaded",
    "sentiment": "loaded"
  }
}
```

---

## Verify Your Work

✅ Engine is running without errors  
✅ Dashboard loads in browser  
✅ Health endpoint returns "healthy"  
✅ Redis shows physics state updates

**Success!** You have a running Curiosity Cottage Quant instance.

---

## What's Next?

Now that you have the engine running:

1. **[How to Run a Backtest](../how-to/01-run-backtest.md)** — Test strategies on historical data
2. **[How to Add a New Strategy](../how-to/02-add-strategy.md)** — Implement your own trading logic
3. **[Architecture Overview](../reference/architecture/data-flow.md)** — Understand the system design

---

## Troubleshooting

### Problem: Redis connection refused

**Symptom:** `ConnectionRefusedError: [Errno 61] Connection refused`

**Solution:**

```bash
# Start Redis
docker-compose up -d redis
# Or
redis-server --daemonize yes
```

### Problem: Chronos model not loading

**Symptom:** `RuntimeError: MPS backend not available`

**Solution:** Ensure you're on Apple Silicon with macOS 12.3+, or the model will fall back to CPU.

### Problem: Alpaca API errors

**Symptom:** `APIError: forbidden`

**Solution:** Verify your API keys in `.env` and ensure you're using Paper Trading URL:

```
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

---

## Summary

In this tutorial, you learned:

- How to set up the development environment
- How to configure API keys
- How to start the trading engine
- How to access the real-time dashboard

---

*Last Updated: 2025-12-21*

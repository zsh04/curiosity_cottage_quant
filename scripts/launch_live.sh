#!/bin/bash
# scripts/launch_live.sh

echo "🚀 IGNITION: Launching Antigravity Prime (Live Data Mode)..."

# 1. Load Environment Variables explicitly
if [ -f .env ]; then
    export $(cat .env | xargs)
    echo "✅ Loaded .env configuration."
else
    echo "❌ ERROR: .env file not found!"
    exit 1
fi

# 2. Validation
if [[ -z "$ALPACA_API_KEY" ]]; then
    echo "❌ CRITICAL: ALPACA_API_KEY is missing."
    exit 1
fi

# 3. Mode Display
echo "DATA FEED: $ALPACA_DATA_FEED"
echo "ENDPOINT:  $ALPACA_BASE_URL"
if [[ "$LIVE_TRADING_ENABLED" == "True" ]]; then
    echo "TRADING:   🔴 LIVE FIRE (Enabled)"
else
    echo "TRADING:   🟢 SIMULATION (ReadOnly / Paper)"
fi

# 4. Launch Main Loop
# Check if run.py exists, else try app/main.py
if [ -f "run.py" ]; then
    python3 run.py
elif [ -f "app/main.py" ]; then
    python3 app/main.py
else
    echo "❌ ERROR: Entrypoint not found (run.py or app/main.py)"
    exit 1
fi

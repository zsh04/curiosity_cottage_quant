# How to Deploy to Production

**Estimated Time:** 30 minutes  
**Difficulty:** Advanced

---

## Overview

This guide shows you how to deploy the Curiosity Cottage Quant engine to a production environment on a Mac Mini or similar bare-metal server.

---

## Before You Begin

Ensure you have:

- A Mac Mini M2/M4 with macOS 13+
- SSH access to the target machine
- Alpaca Live Trading account (not paper)
- Domain name (optional, for remote access)

---

## Steps

### 1. Prepare the Server

SSH into your Mac Mini:

```bash
ssh admin@your-mac-mini.local
```

Install dependencies:

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install system dependencies
brew install python@3.11 redis git
```

### 2. Clone and Configure

```bash
cd /opt
git clone https://github.com/your-org/curiosity_cottage_quant.git cc-engine
cd cc-engine

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements-metal.txt
```

### 3. Configure Production Environment

Create production `.env`:

```bash
cat > .env << 'EOF'
# Production Configuration
ENVIRONMENT=production

# Alpaca LIVE (not paper!)
ALPACA_API_KEY=your_live_key
ALPACA_API_SECRET=your_live_secret
ALPACA_BASE_URL=https://api.alpaca.markets

# Redis
REDIS_URL=redis://localhost:6379

# Telemetry
GRAFANA_CLOUD_API_KEY=your_grafana_key
GRAFANA_CLOUD_ENDPOINT=https://your-stack.grafana.net

# Safety
MAX_POSITION_SIZE=0.10
DAILY_LOSS_LIMIT=0.02
EOF
```

> [!CAUTION]
> Never commit `.env` to version control. Verify with `git status`.

### 4. Start Redis

```bash
brew services start redis
```

Verify:

```bash
redis-cli ping
# PONG
```

### 5. Create systemd-like Launch Agent

Create a launchd plist for auto-start:

```bash
cat > ~/Library/LaunchAgents/com.cc.engine.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cc.engine</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/cc-engine/.venv/bin/python</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>app.main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/opt/cc-engine</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/cc-engine.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/cc-engine.error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/cc-engine/.venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
```

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.cc.engine.plist
```

### 6. Verify Deployment

Check the engine is running:

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

Check logs:

```bash
tail -f /var/log/cc-engine.log
```

### 7. Configure Firewall (Optional)

If you need remote access:

```bash
# Allow port 8000
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/cc-engine/.venv/bin/python
```

### 8. Set Up Monitoring

Configure Grafana Cloud alerting:

1. Log into Grafana Cloud
2. Create dashboard for `cc_*` metrics
3. Set up alerts:
   - `cc.physics.alpha < 2.0` → Critical (Physics Veto)
   - Engine offline > 1 minute → Page

---

## Verify

- [ ] Engine responds to health check
- [ ] Redis is connected
- [ ] Metrics appear in Grafana
- [ ] Logs show normal operation
- [ ] Positions sync with Alpaca

---

## Common Variations

### Run with Multiple Workers

For higher throughput (not recommended for trading):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Use nginx as Reverse Proxy

```nginx
server {
    listen 80;
    server_name trading.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Service won't start | Check `/var/log/cc-engine.error.log` |
| Alpaca authentication fails | Verify API keys are for LIVE, not paper |
| MPS not available | Ensure macOS 12.3+ and M-series chip |
| Redis connection refused | `brew services restart redis` |

---

## Rollback Procedure

If something goes wrong:

```bash
# 1. Stop the engine
launchctl unload ~/Library/LaunchAgents/com.cc.engine.plist

# 2. Revert to previous version
cd /opt/cc-engine
git checkout v0.9.0

# 3. Restart
launchctl load ~/Library/LaunchAgents/com.cc.engine.plist
```

---

## Related

- [Quickstart Tutorial](../tutorials/01-quickstart.md)
- [Emergency Procedures](../operations/emergency.md)

---

*Last Updated: 2025-12-21*

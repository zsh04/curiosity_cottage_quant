# Emergency Procedures (The Grim Trigger)

## Level 1: Soft Stop

If parameters drift out of bounds (Drawdown > 2%):

- **Action**: The system auto-switches to `TradingStatus.HALTED_DRAWDOWN`.
- **Manual Override**: Run `python scripts/emergency_shutdown.py`.

## Level 2: Hard Kill (Process Hang)

If the Python process is unresponsive:

```bash
pkill -f "main.py"
```

## Level 3: Liquidation (The Red Button)

To immediately liquidate all open positions:

```bash
python scripts/flatten_all.py --force
```

**WARNING**: This will execute market sell orders for everything. Use only if solvency is at risk.

# How to Run a Backtest

**Estimated Time:** 5 minutes  
**Difficulty:** Beginner

---

## Overview

This guide shows you how to run a backtest on historical data using the built-in backtest engine.

---

## Before You Begin

Ensure you have:

- The engine installed ([Quickstart Tutorial](../tutorials/01-quickstart.md))
- Historical data in QuestDB (or Yahoo Finance access)

---

## Steps

### 1. Choose a Strategy

Available strategies in `app/strategies/`:

| Strategy | Description |
|----------|-------------|
| `momentum` | Trend-following based on velocity |
| `mean_reversion` | Mean reversion with Bollinger Bands |
| `breakout` | Volatility breakout signals |
| `volatility` | Volatility regime adaptation |
| `lstm` | Reservoir computing (ESN) |

### 2. Run the Backtest Script

```bash
python scripts/run_backtest.py --strategy momentum --symbol SPY --start 2024-01-01 --end 2024-12-01
```

**Parameters:**

| Flag | Description | Default |
|------|-------------|---------|
| `--strategy` | Strategy name | `momentum` |
| `--symbol` | Ticker symbol | `SPY` |
| `--start` | Start date (YYYY-MM-DD) | 1 year ago |
| `--end` | End date (YYYY-MM-DD) | Today |
| `--capital` | Initial capital | `100000` |

### 3. View Results

The script outputs:

```
═══════════════════════════════════════════════════════
                    BACKTEST RESULTS
═══════════════════════════════════════════════════════
Strategy:        Momentum
Symbol:          SPY
Period:          2024-01-01 to 2024-12-01

PERFORMANCE
───────────────────────────────────────────────────────
Sharpe Ratio:    1.42
Total Return:    18.3%
Max Drawdown:    -8.2%
Win Rate:        54.2%
Total Trades:    127

VALIDATION
───────────────────────────────────────────────────────
✅ Sharpe >= 1.0
✅ Return > 15%
⚠️  Drawdown > 5% (monitor)
═══════════════════════════════════════════════════════
```

### 4. Export Results (Optional)

Save results to JSON:

```bash
python scripts/run_backtest.py --strategy momentum --symbol SPY --output results.json
```

Results are also saved to `backtest_results/` automatically.

---

## Verify

Confirm the backtest completed:

```bash
ls backtest_results/
# momentum_SPY_2024-01-01_2024-12-01.json
```

---

## Common Variations

### Run Multiple Symbols

```bash
for symbol in SPY QQQ AAPL TSLA; do
    python scripts/run_backtest.py --strategy momentum --symbol $symbol
done
```

### Compare Strategies

```bash
python scripts/run_backtest.py --strategy momentum --symbol SPY
python scripts/run_backtest.py --strategy mean_reversion --symbol SPY
python scripts/run_backtest.py --strategy breakout --symbol SPY
```

### With Physics Veto Enabled

The Physics Veto is enabled by default. It blocks trades when α < 2.0:

```bash
python scripts/run_backtest.py --strategy momentum --symbol SPY --physics-veto
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No data for symbol" | Ensure QuestDB has historical data or run `scripts/backfill_tier1.py` |
| "Strategy not found" | Check strategy name matches file in `app/strategies/` |
| Low Sharpe Ratio | Try different date ranges or symbols |

---

## Related

- [How to Add a New Strategy](./02-add-strategy.md)
- [Backtest Engine Reference](../reference/architecture/backtest-engine.md)

---

*Last Updated: 2025-12-21*

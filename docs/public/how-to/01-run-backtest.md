# How to Run a Quantum Holodeck Simulation

**Estimated Time:** 5-10 minutes  
**Difficulty:** Intermediate

---

## Overview

The **Quantum Holodeck** is a full-system simulation that backtests the "Oracle" (Chronos) and "Hippocampus" (Market Memory) across a historical timeline. It runs the entire forecasting engine, not just a simple strategy function.

---

## Before You Begin

Ensure you have:

1. **Tier 1 Data** in QuestDB (run `scripts/backfill_tier1.py`).
2. **Market Memory** ingested (run `scripts/ingest_memory.py`).
3. **MPS/GPU** recommended (Inference is heavy).

---

## Steps

### 1. Run the Backtest Script

```bash
# Run a 6-month simulation
python scripts/run_backtest.py --start 2023-01-01 --end 2023-06-01 --plot
```

**Parameters:**

| Flag | Description | Format |
|------|-------------|--------|
| `--start` | Simulation Start Date | YYYY-MM-DD |
| `--end` | Simulation End Date | YYYY-MM-DD |
| `--plot` | Generate Equity Curve image | (Flag) |

### 2. View Results

The script will output a simulated trading report:

```
==============================
 BACKTEST REPORT
==============================
Return: 12.45%
Sharpe: 1.82
Max DD: -5.30%
==============================
```

If `--plot` is used, check the current directory for **`backtest_equity.png`**.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No data loaded" | Check QuestDB. Ensure requested date range exists. |
| "Slow performance" | Computation is heavy (Neural Inference + Vector Search). Use a shorter time range for testing. |
| "0 Trades" | Check if Memory is populated or if Confidence thresholds are too high. |

---

*Last Updated: 2025-12-21*

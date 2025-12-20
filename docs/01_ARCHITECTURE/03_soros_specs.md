# Service Specification: Soros (The Philosopher)

**Type:** FastStream Application (Docker) + Host Bridge (ANE)
**Role:** The Reflexivity Engine (Signal Generation & Logic Gates)
**Cycle:** Event-Driven (Post-Physics)

## Interface

* **Input Topic:** `physics.forces` (Consumes `ForceVector`)
* **Output Topic:** `strategy.signals` (Publishes `TradeSignal`)

## Data Structures

### TradeSignal Schema

```json
{
  "timestamp": "iso8601 string",
  "symbol": "string",
  "side": "enum(BUY, SELL, HOLD)",
  "strength": "float (0.0 - 1.0)",
  "price": "float (reference)",
  "meta": {
    "thesis": "string (e.g., CLEAN_UP_TREND)",
    "veto": "string (e.g., CHAOS_DETECTED, ALPHA_TOO_LOW)",
    "alpha": "float",
    "entropy": "float"
  }
}
```

## The Logic Gates (Reflexivity)

1. **Gate 1: The Alpha Veto (Tail Risk)**
   * **Math:** $\alpha \le 2.0 \implies \text{Infinite Variance / Lévy Regime}$.
   * **Action:** `VETO` (HOLD). Only trade when finite variance is probable ($\alpha > 2.0$).

2. **Gate 2: The Chaos Veto (Entropy)**
   * **Math:** $H(X) > 0.8 \implies \text{High Disorder}$.
   * **Action:** `VETO` (HOLD). Signal-to-noise ratio is too poor.

3. **Gate 3: Momentum & Nash**
   * **Buy:** Momentum $> 0$ AND NashDistance $< 2.0$ (Uptrend, not overbought).
   * **Sell:** Momentum $< 0$ AND NashDistance $> -2.0$ (Downtrend, not oversold).
   * **Else:** `HOLD` (Mean Reversion / Chop).

## Infrastructure

* **Neural Engine:** `metal/soros_ane.py` runs natively on macOS Host.
* **Model:** FinBERT (CoreML `.mlpackage`) on ANE.
* **Bridge:** Publishes sentiment heartbeats to Redis (`sentiment.heartbeat`), consumed by Soros (Future).

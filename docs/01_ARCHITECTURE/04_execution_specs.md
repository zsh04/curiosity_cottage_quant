# Service Specification: Execution (The Gatekeeper)

**Type:** FastStream Application (Docker)
**Role:** Risk Management & Order Generation
**Identity:** Nassim Taleb (Paranoid)

## Interface

* **Input Topic:** `strategy.signals` (Consumes `TradeSignal`)
* **Output Topic:** `execution.orders` (Publishes `OrderPacket`)

## Data Structures

### OrderPacket Schema

```json
{
  "timestamp": "iso8601 string",
  "signal_id": "uuid string",
  "symbol": "string",
  "side": "enum(BUY, SELL)",
  "quantity": "float",
  "order_type": "MARKET",
  "risk_check_passed": "boolean"
}
```

## The Risk Gates (Ruin Constraints)

1. **Gate 1: The Hard Stop (Capital Preservation)**
   * **Rule:** If `Daily Loss` $\ge 2\%$ of Starting NAV.
   * **Action:** `BLOCK`. Cease all trading explicitly. Log "RISK BREACH".

2. **Gate 2: Position Sizing (The Kelly Fraction)**
   * **Rule:** Conservative Fixed-Fractional (Phase 1).
   * **Formula:** $Qty = \frac{\text{NAV} \times 0.01}{\text{Price}}$.
   * **Effect:** Limits notional exposure to 1% of equity per trade.

3. **Gate 3: Filter**
   * **Rule:** `Side == HOLD`.
   * **Action:** Ignore.

# Service Specification: Chronos (The GPU Mind)

**Type:** FastStream Application (Docker)
**Role:** Probabilistic Time-Series Forecasting
**Hardware:** Scaled Dot-Product Attention on Apple Silicon (MPS)
**Identity:** Jim Simons

## Interface

* **Input Topic:** `market.tick.{symbol}` (Websocket Stream)
* **Output Topic:** `forecast.signals` (Publishes `ForecastPacket`)

## Data Structures

### ForecastPacket Schema

```json
{
  "timestamp": "iso8601 string",
  "symbol": "string",
  "p10": "float (Bearish Case)",
  "p50": "float (Base Case)",
  "p90": "float (Bullish Case)",
  "horizon": "integer (e.g., 10)",
  "confidence": "float (0.0 - 1.0)"
}
```

## Neural Architecture

* **Model:** `amazon/chronos-t5-tiny` (Pretrained Foundation Model).
* **Tokenization:** Values are quantized and tokenized; input is treated as language.
* **Context Window:** 512 Ticks (Rolling Buffer).
* **Sampling:** 20 Sample Paths generated per inference step.

## Inference Strategy

1. **Throttling:** Run inference only every $N=10$ ticks to balance compute/latency.
2. **Quantiles:**
   * **P10:** 10th Percentile of sample paths at $T+Horizon$.
   * **P50:** Median path.
   * **P90:** 90th Percentile.
3. **Confidence Metric:** Derived from the spread.
   $$ \text{Spread} = \frac{P90 - P10}{P50} $$
   $$ \text{Confidence} = \max(0, 1.0 - (\text{Spread} \times 10)) $$

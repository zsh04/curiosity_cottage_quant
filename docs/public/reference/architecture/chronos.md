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

* **Model:** `amazon/chronos-bolt-small` (High-Performance Foundation Model).
* **Tokenization:** Values are quantized and tokenized; input is treated as language.
* **Context Window:** 512 Ticks (Rolling Buffer).
* **Sampling:** Direct Quantile Prediction (No auto-regressive sampling needed).

## Inference Strategy

1. **Throttling:** Run inference only every $N=10$ ticks to balance compute/latency.
2. **Quantiles:**
   * **P10:** Direct output from `ChronosBoltPipeline`.
   * **P50:** Median forecast.
   * **P90:** Bullish case.
3. **Confidence Metric:** Derived from the spread.
   $$ \text{Spread} = \frac{P90 - P10}{P50} $$
   $$ \text{Confidence} = \max(0, 1.0 - (\text{Spread} \times 10)) $$

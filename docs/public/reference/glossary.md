# 📖 Glossary of Terms

**Purpose:** Definitive reference for all terminology used in Curiosity Cottage Quant.

---

## A

### Alpha (α)

**Context:** Risk Management, Statistics  
**Definition:** The tail exponent from the Hill Estimator, measuring the heaviness of distribution tails.  
**Range:** 0.5 to 10.0 (typically 1.5 to 4.0 for financial data)  
**Critical Threshold:** α = 2.0 (below this, variance is infinite → Physics Veto)  
**See Also:** [Hill Estimator](./04_hill_estimator.md), Physics Veto

### Agent

**Context:** LangGraph, Architecture  
**Definition:** An autonomous component in the cognitive pipeline (e.g., AnalystAgent, ExecutionAgent).  
**Implementation:** `app/agent/nodes/*.py`

### ANN (Approximate Nearest Neighbor)

**Context:** LanceDB, Vector Search  
**Definition:** Algorithm for fast similarity search that trades perfect accuracy for speed.  
**Performance:** ~100x faster than brute-force with 95% recall

---

## B

### BES (Bayesian Expected Shortfall)

**Context:** Position Sizing  
**Definition:** A position sizing methodology combining Kelly Criterion with Expected Shortfall risk measure.  
**Formula:** $f = \lambda(\alpha) \cdot \frac{E[R] - r_f}{ES}$  
**See Also:** [Kelly Sizing](./05_kelly_sizing.md), Lambda

### BFF (Backend for Frontend)

**Context:** Architecture  
**Definition:** A Node.js server that proxies and aggregates backend data for the React frontend.  
**Location:** `bff/server.js`

### BLUE (Best Linear Unbiased Estimator)

**Context:** Kalman Filter, Statistics  
**Definition:** An estimator that achieves minimum variance among all linear unbiased estimators.  
**Significance:** The Kalman Filter produces BLUE estimates under Gaussian assumptions.

### Bolt (Chronos-Bolt)

**Context:** Forecasting  
**Definition:** Amazon's optimized Chronos model variant designed for direct quantile prediction.  
**Model:** `amazon/chronos-bolt-small`  
**Output:** P10, P50, P90 quantiles (not sample-based)

---

## C

### Chronos

**Context:** Forecasting Service  
**Definition:** Amazon's pretrained time-series forecasting model based on T5 architecture.  
**Service:** `app/services/chronos.py`  
**Hardware:** MPS (Apple Metal) or CPU

### Council

**Context:** Strategy Voting  
**Definition:** Ensemble system that aggregates signals from multiple trading strategies.  
**Strategies:** Momentum, Mean Reversion, Breakout, Volatility, LSTM  
**See Also:** [Council Specs](../01_ARCHITECTURE/09_council_specs.md)

### Critical Regime

**Context:** Physics Engine, Risk  
**Definition:** Market state where α ≤ 2.0, indicating infinite variance. **All trading is vetoed.**  
**Action:** Position size = 0.0

---

## D

### Debate Console

**Context:** Frontend  
**Definition:** UI component displaying LLM reasoning chains and multi-agent "debate" outputs.  
**Component:** `frontend/src/components/DebateConsole.tsx`

---

## E

### ES (Expected Shortfall)

**Context:** Risk Management  
**Definition:** Average loss in the worst (1-α)% of cases. Also called CVaR (Conditional Value at Risk).  
**Formula (Gaussian):** $ES_\alpha = \sigma \cdot \frac{\phi(z_\alpha)}{1 - \alpha}$  
**Benefit:** Coherent risk measure (unlike VaR)

### Entropy

**Context:** Physics Engine  
**Definition:** Measure of market disorder/unpredictability in the 5-Pillar model.  
**Range:** 0.0 to 1.0 (higher = more chaotic)

---

## F

### Feynman Service

**Context:** Physics Engine  
**Definition:** Core service that computes the 5-Pillar Physics Vector for each symbol.  
**Named After:** Richard Feynman (physicist)  
**Output:** Mass, Momentum, Friction, Entropy, Nash Distance

### FinBERT

**Context:** Sentiment Analysis  
**Definition:** BERT model fine-tuned on financial text for sentiment classification.  
**Execution:** ONNX Runtime (CPU-optimized)  
**Output:** Bullish/Neutral/Bearish + confidence score

### Five Pillars

**Context:** Physics Engine  
**Definition:** The five fundamental forces in the market physics model:

1. **Mass** - Inertia/resistance to movement
2. **Momentum** - Directional force
3. **Friction** - Dampening coefficient
4. **Entropy** - Disorder measure
5. **Nash Distance** - Distance from Nash equilibrium

### Friction

**Context:** Physics Engine  
**Definition:** Resistance coefficient in the 5-Pillar model, representing market dampening.  
**Range:** 0.0 to 1.0

---

## G

### Gaussian Regime

**Context:** Physics Engine, Risk  
**Definition:** Market state where α > 3.0, indicating normal (thin-tailed) distribution.  
**Action:** Full trading permitted (leverage cap: 1.0)

### Glassmorphism

**Context:** Frontend Design  
**Definition:** UI design trend featuring frosted glass effects with blur and transparency.  
**Implementation:** `backdrop-filter: blur()` + semi-transparent backgrounds

---

## H

### Hill Estimator

**Context:** Statistics, Risk  
**Definition:** Maximum likelihood estimator for the tail exponent of power-law distributions.  
**Formula:** $\hat{\alpha}_H = \frac{1}{\frac{1}{k}\sum_{i=1}^{k}\ln\frac{X_{(n-i+1)}}{X_{(n-k)}}}$  
**See Also:** [Hill Estimator Spec](./04_hill_estimator.md)

### Hurst Exponent

**Context:** Time Series Analysis  
**Definition:** Measure of long-term memory in a time series.  
**Range:** 0 to 1  

- H < 0.5: Mean-reverting
- H = 0.5: Random walk
- H > 0.5: Trending

---

## I

### IVF (Inverted File)

**Context:** LanceDB, Vector Search  
**Definition:** Index structure for approximate nearest neighbor search using clustering.  
**Parameters:** num_partitions, num_sub_vectors

---

## K

### Kalman Filter

**Context:** State Estimation  
**Definition:** Optimal recursive algorithm for estimating hidden state from noisy observations.  
**State Vector:** [Position, Velocity, Acceleration]  
**See Also:** [Kalman Filter Spec](./03_kalman_filter.md)

### Kalman Gain

**Context:** Kalman Filter  
**Definition:** Weighting factor determining how much to trust new observations vs. predictions.  
**Symbol:** $\mathbf{K}_k$  
**Formula:** $\mathbf{K}_k = \mathbf{P}_{k|k-1}\mathbf{H}^T\mathbf{S}_k^{-1}$

### Kelly Criterion

**Context:** Position Sizing  
**Definition:** Optimal betting fraction to maximize long-term growth rate.  
**Classic Formula:** $f^* = \frac{p \cdot b - q}{b}$ (where p=win prob, b=odds, q=1-p)  
**Modified (BES):** Uses Expected Shortfall instead of fixed odds

---

## L

### Lambda (λ)

**Context:** Position Sizing  
**Definition:** Conviction scaling factor based on tail thickness (α).  
**Formula:**

- α ≤ 2.0: λ = 0.0 (VETO)
- 2.0 < α ≤ 3.0: λ = α - 2.0
- α > 3.0: λ = 1.0

### LanceDB

**Context:** Storage  
**Definition:** Embedded vector database for similarity search on market state embeddings.  
**Location:** `data/lancedb/`

### LangGraph

**Context:** Agent Framework  
**Definition:** Library for building stateful, multi-actor LLM applications with graph-based workflows.  
**Implementation:** `app/agent/graph.py`

### Lévy Stable Regime

**Context:** Physics Engine, Risk  
**Definition:** Market state where 2.0 < α ≤ 3.0, indicating fat tails but finite variance.  
**Action:** Reduced trading (leverage cap: 0.5)

### Llama 3.1

**Context:** LLM  
**Definition:** Meta's open-source large language model used for reasoning.  
**Execution:** Ollama (local inference)  
**Model:** `llama3.1:8b`

---

## M

### Mass

**Context:** Physics Engine  
**Definition:** Base inertia in the 5-Pillar model, representing resistance to price movement.  
**Range:** 0.0 to 1.0

### Momentum

**Context:** Physics Engine  
**Definition:** Directional force in the 5-Pillar model.  
**Range:** -∞ to +∞ (positive = bullish, negative = bearish)

### MPS (Metal Performance Shaders)

**Context:** Hardware  
**Definition:** Apple's GPU compute framework for machine learning on Mac.  
**Used By:** Chronos-Bolt, PyTorch

---

## N

### Nash Distance

**Context:** Physics Engine  
**Definition:** Distance from Nash Equilibrium in the 5-Pillar model.  
**Range:** 0.0 to 1.0 (0 = at equilibrium)

---

## O

### ONNX (Open Neural Network Exchange)

**Context:** ML Inference  
**Definition:** Open format for ML models enabling cross-platform inference.  
**Used By:** SentimentAdapter (FinBERT via ONNX Runtime)

### orjson

**Context:** Serialization  
**Definition:** Fast JSON library for Python, optimized for high-frequency data.  
**Performance:** 3-10x faster than standard json library

---

## P

### P10/P50/P90

**Context:** Forecasting  
**Definition:** Prediction quantiles from Chronos:

- **P10:** 10th percentile (pessimistic)
- **P50:** Median (central estimate)
- **P90:** 90th percentile (optimistic)

### Physics Veto

**Context:** Risk Management  
**Definition:** Automatic trade blocking when α ≤ 2.0 (Critical Regime).  
**Rationale:** Infinite variance makes position sizing undefined.  
**See Also:** [Physics V4](./02_physics_v4.md)

### Power Law

**Context:** Statistics  
**Definition:** Distribution where probability decays as $P(X > x) \propto x^{-\alpha}$.  
**Significance:** Financial returns often follow power laws in the tails.

### ProTerminal

**Context:** Frontend  
**Definition:** Main trading terminal component with tabs for charts, console, agents, models.  
**Component:** `frontend/src/components/ProTerminal.tsx`

---

## Q

### QuestDB

**Context:** Storage  
**Definition:** Time-series database optimized for high-frequency financial data.  
**Tables:** `trades`, `ohlcv_1d`  
**Protocol:** PostgreSQL wire (port 8812) + InfluxDB Line Protocol (port 9009)

---

## R

### Regime

**Context:** Physics Engine  
**Definition:** Market classification based on tail behavior:

1. **Gaussian** (α > 3.0)
2. **Lévy Stable** (2.0 < α ≤ 3.0)
3. **Critical** (α ≤ 2.0)

### RUM (Real User Monitoring)

**Context:** Observability  
**Definition:** Frontend monitoring collecting actual user performance metrics.  
**Implementation:** Grafana Faro (`frontend/src/telemetry.ts`)

---

## S

### Sharpe Ratio

**Context:** Performance Metrics  
**Definition:** Risk-adjusted return metric.  
**Formula:** $SR = \frac{\mu}{\sigma} \times \sqrt{252}$  
**Threshold:** ≥ 1.0 required for strategy validation

### State Vector

**Context:** Kalman Filter  
**Definition:** The hidden state being estimated: $\mathbf{x}_k = [p_k, v_k, a_k]^T$

- $p_k$: Position (log price)
- $v_k$: Velocity (returns)
- $a_k$: Acceleration (momentum change)

---

## T

### TELEMETRY Packet

**Context:** WebSocket Protocol  
**Definition:** Real-time data structure broadcast to frontend at 1 Hz.  
**Fields:** symbol, price, physics, forecast, sentiment, position, agents, models  
**See Also:** [WebSocket Protocol](../02_API/02_websocket_protocol.md)

### Tail Exponent

**Context:** Statistics  
**Definition:** Parameter α determining how heavy the distribution tails are.  
**Synonym:** Alpha, Hill Estimator output

---

## V

### VaR (Value at Risk)

**Context:** Risk Management  
**Definition:** Maximum expected loss at a given confidence level.  
**Limitation:** Not a coherent risk measure (can underestimate tail risk)  
**Alternative:** Expected Shortfall (ES)

### Vector Embedding

**Context:** LanceDB, Memory  
**Definition:** 384-dimensional representation of market state for similarity search.  
**Model:** `all-MiniLM-L6-v2` (sentence-transformers)

---

## W

### WAL (Write-Ahead Log)

**Context:** QuestDB  
**Definition:** Durability mechanism ensuring data is logged before acknowledgment.  
**Purpose:** Crash recovery

---

## Symbols

### $\alpha$ (Alpha)

**See:** Alpha, Hill Estimator

### $\lambda$ (Lambda)

**See:** Lambda

### $\sigma$ (Sigma)

**Context:** Statistics  
**Definition:** Standard deviation of returns  
**Derived From:** Chronos spread: $\sigma = \frac{P90 - P10}{2.56}$

### $\mu$ (Mu)

**Context:** Statistics  
**Definition:** Mean (expected) return

### $\mathbf{F}$ (F Matrix)

**Context:** Kalman Filter  
**Definition:** State transition matrix

### $\mathbf{K}$ (K Matrix)

**Context:** Kalman Filter  
**Definition:** Kalman Gain matrix

### $\mathbf{P}$ (P Matrix)

**Context:** Kalman Filter  
**Definition:** Error covariance matrix

---

## Acronyms

| Acronym | Full Form |
|---------|-----------|
| ANN | Approximate Nearest Neighbor |
| AOF | Append-Only File (Redis) |
| BES | Bayesian Expected Shortfall |
| BFF | Backend for Frontend |
| BLUE | Best Linear Unbiased Estimator |
| CVaR | Conditional Value at Risk |
| DDL | Data Definition Language |
| ES | Expected Shortfall |
| HFT | High-Frequency Trading |
| IVF | Inverted File (index) |
| MPS | Metal Performance Shaders |
| OHLCV | Open, High, Low, Close, Volume |
| ONNX | Open Neural Network Exchange |
| PQ | Product Quantization |
| RDB | Redis Database (snapshot) |
| RTO | Recovery Time Objective |
| RPO | Recovery Point Objective |
| RUM | Real User Monitoring |
| SLA | Service Level Agreement |
| TTL | Time To Live |
| VaR | Value at Risk |
| WAL | Write-Ahead Log |

---

*Last Updated: 2025-12-21*

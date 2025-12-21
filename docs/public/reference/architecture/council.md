# Service Specification: The Council (Algorithm Registry)

**Type:** Python Module (`app/strategies`)
**Role:** The Quantitative Expert Panel
**Cycle:** On-Demand (Analyst Cycle)

## Interface

* **Input:** `pandas.DataFrame` (columns: `close`, indexed by `datetime`)
* **Output:** `float` (-1.0 to 1.0)
  * `-1.0`: Strong Sell
  * `0.0`: Neutral/Flat
  * `1.0`: Strong Buy

## The Experts

### 1. KalmanMomentum (`trend.py`)

* **Philosophy:** "Trend is Physics."
* **Mechanism:** Uses a Kalman Filter to extract the "true" velocity of price, ignoring noise.
* **Signal:**
  * Velocity > 0: **BUY**
  * Velocity < 0: **SELL**

### 2. BollingerReversion (`mean_reversion.py`)

* **Philosophy:** "What goes up must come down."
* **Mechanism:** Statistical deviations (Z-Score) from a moving average.
* **Signal:**
  * Price > Upper Band (2σ): **SELL**
  * Price < Lower Band (2σ): **BUY**

### 3. FractalBreakout (`breakout.py`)

* **Philosophy:** "Geometry defines structure."
* **Mechanism:** Identifies support/resistance levels using fractal geometry (n-period highs/lows).
* **Signal:**
  * Break above resistance: **BUY**
  * Break below support: **SELL**

### 4. QuantumOscillator (`quantum.py`)

* **Philosophy:** "Market is a Wavefunction."
* **Mechanism:** Calculates probability amplitudes based on price energy states.
* **Signal:**
  * Energy State High (Overbought): **SELL**
  * Energy State Low (Oversold): **BUY**

### 5. MoonPhase (`moon_phase.py`)

* **Philosophy:** "Nature governs tides."
* **Mechanism:** Astro-financing (Lunar Cycle correlation).
* **Signal:**
  * New Moon: **BUY**
  * Full Moon: **SELL**

## Integration Strategy

* **Host:** `AnalystAgent` (`app/agent/nodes/analyst.py`)
* **Method:** `calculate_signal(df)`
* **Usage:** All enabled strategies are run in parallel. Their outputs are aggregated into a `strat_signals` dictionary and injected into the Reasoning Engine (LLM) for synthesis.

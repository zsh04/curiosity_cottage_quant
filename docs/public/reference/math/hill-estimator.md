# Mathematical Specification: Hill Estimator for Heavy Tails

**Location:** `app/lib/physics/heavy_tail.py`  
**Purpose:** Estimate the tail exponent ($\alpha$) to detect infinite-variance regimes  
**Method:** Hill Estimator (Maximum Likelihood for Pareto tails)

## 1. Theoretical Foundation

### 1.1 Power Law Distributions

Financial returns often exhibit **heavy tails** that follow a Power Law:

$$
P(X > x) \sim x^{-\alpha} \quad \text{as } x \to \infty
$$

Where:

- $\alpha$ = **Tail Index** (controls tail heaviness)
- Lower $\alpha$ → Heavier tails → More extreme events

**Implications:**

- $\alpha > 2$: Finite variance (Gaussian-like)
- $1 < \alpha < 2$: **Infinite variance** (Lévy Stable)
- $\alpha \leq 1$: Infinite mean (Cauchy-like, Critical)

## 2. Hill Estimator

The Hill Estimator provides a **Maximum Likelihood estimate** of $\alpha$ for Power Law tails.

### 2.1 Formula

For the **k largest** order statistics from a sample of size $n$:

$$
\hat{\alpha}_H = \frac{1}{\frac{1}{k} \sum_{i=1}^{k} \ln\left(\frac{X_{(i)}}{X_{(k+1)}}\right)}
$$

Where:

- $X_{(1)} \geq X_{(2)} \geq \cdots \geq X_{(n)}$ (sorted descending)
- $X_{(k+1)}$ = Threshold (minimum value of the tail)
- $k$ = Number of tail observations (adaptive based on sample size)

**Intuition**: Measures the average relative log-distance of tail points from the threshold.

### 2.2 Derivation (Sketch)

For Pareto distribution $P(X > x) = (x_{\min}/x)^\alpha$:

$$
\ln X \sim \text{Exponential}(\alpha^{-1})
$$

Maximum Likelihood estimate of $\alpha^{-1}$:

$$
\frac{1}{\hat{\alpha}} = \frac{1}{k} \sum_{i=1}^{k} \ln\left(\frac{X_{(i)}}{X_{(k+1)}}\right)
$$

Inverting gives the Hill Estimator.

## 3. Implementation Details

### 3.1 Data Preparation

**Input**: Time series of returns (or any financial data)

**Step 1**: Take **absolute values** (we care about magnitude, not direction)

$$
Y_i = |R_i|
$$

**Step 2**: Sort in **descending order**

$$
Y_{(1)} \geq Y_{(2)} \geq \cdots \geq Y_{(n)}
$$

### 3.2 Adaptive Tail Selection

**Challenge**: Choosing $k$ (tail size) is crucial:

- Too small → High variance (unstable estimate)
- Too large → Bias (includes non-tail data)

**Solution**: **Adaptive thresholding** based on sample size:

| Sample Size $n$ | Tail Percentile | Rationale |
|-----------------|-----------------|-----------|
| $n < 30$ | 10% | Small sample → use more data |
| $30 \leq n < 500$ | 5% | Standard choice |
| $n \geq 500$ | 3% | Large sample → precision |

**Minimum Tail Size**: $k \geq 10$ (for statistical reliability)

**Implementation:**

```python
if n < 30:
    tail_percentile = 0.10
elif n < 500:
    tail_percentile = 0.05
else:
    tail_percentile = 0.03

k = max(int(n * tail_percentile), 10)
```

### 3.3 Hill Calculation

```python
# Select tail
tail = sorted_data[:k]  # Top k largest values
x_min = sorted_data[k]  # Threshold

# Compute log ratios
log_ratios = np.log(tail / x_min)

# Hill estimator
hill_value = np.mean(log_ratios)
alpha = 1.0 / hill_value
```

### 3.4 Numerical Safeguards

**Problem 1**: $X_{(k+1)} \leq 0$ (undefined log)

**Solution**: Return default $\alpha = 3.0$ (Gaussian assumption)

**Problem 2**: $\text{hill\_value} \leq 0$ (mathematical impossibility)

**Solution**: Return default $\alpha = 3.0$

**Problem 3**: Extreme $\alpha$ values (numerical instability)

**Solution**: **Clamp to [0.5, 10.0]**

```python
alpha = np.clip(alpha, 0.5, 10.0)
```

## 4. Regime Classification

Based on $\hat{\alpha}$, we classify the market into **three regimes**:

### 4.1 Regime Definitions

| Regime | Condition | Leverage Cap | Interpretation |
|--------|-----------|--------------|----------------|
| **Gaussian** | $\alpha > 3.0$ | 1.0 (100%) | Finite variance, safe for trading |
| **Lévy Stable** | $2.0 < \alpha \leq 3.0$ | 0.5 (50%) | Infinite variance, reduce exposure |
| **Critical** | $\alpha \leq 2.0$ | 0.0 (**VETO**) | Extreme tails, **no trading** |

### 4.2 Classification Logic

```python
def get_regime(alpha: float) -> RegimeMetrics:
    if alpha > 3.0:
        return RegimeMetrics(
            alpha=alpha,
            regime=Regime.GAUSSIAN,
            leverage_cap=1.0
        )
    elif 2.0 < alpha <= 3.0:
        return RegimeMetrics(
            alpha=alpha,
            regime=Regime.LEVY_STABLE,
            leverage_cap=0.5
        )
    else:  # alpha <= 2.0
        return RegimeMetrics(
            alpha=alpha,
            regime=Regime.CRITICAL,
            leverage_cap=0.0  # VETO
        )
```

## 5. Mathematical Properties

### 5.1 Asymptotic Normality

For large $k$, the Hill estimator is **asymptotically normal**:

$$
\sqrt{k} \left( \hat{\alpha}_H - \alpha \right) \xrightarrow{d} \mathcal{N}(0, \alpha^2)
$$

**Implication**: Standard error $\approx \frac{\alpha}{\sqrt{k}}$

**Example**: For $\alpha = 2.5$, $k = 50$:
$$
\text{SE} \approx \frac{2.5}{\sqrt{50}} = 0.35
$$

### 5.2 Bias-Variance Tradeoff

- **Increasing $k$**:
  - ✅ Reduces variance (more data)
  - ❌ Increases bias (includes non-tail observations)
  
- **Decreasing $k$**:
  - ✅ Reduces bias (pure tail)
  - ❌ Increases variance (fewer data points)

**Optimal $k$**: Typically $k \approx \sqrt{n}$ to $0.1n$ (varies by application)

## 6. Usage Examples

### 6.1 Standalone

```python
from app.lib.physics.heavy_tail import HeavyTailEstimator

# Sample returns
returns = np.random.randn(252) * 0.01  # 1 year daily

# Estimate alpha
alpha = HeavyTailEstimator.hill_estimator(returns)
print(f"Tail Index: {alpha:.2f}")

# Get regime
regime = HeavyTailEstimator.get_regime(alpha)
print(f"Regime: {regime.regime.value}")
print(f"Leverage Cap: {regime.leverage_cap}")
```

### 6.2 Streaming (Online)

```python
estimator = HeavyTailEstimator(window_size=100)

for ret in live_returns:
    estimator.update(ret)
    alpha = estimator.get_current_alpha()
    
    if alpha < 2.0:
        print("⚠️ CRITICAL REGIME - VETO TRADING")
```

## 7. Integration with Physics Veto

### 7.1 Backtest Engine

```python
regime_analysis = physics_service.analyze_regime(regime_window)
alpha = regime_analysis.get("alpha", 3.0)

if alpha < 2.0:
    signal = 0.0  # VETO
```

### 7.2 Real-Time Trading

```python
# In FeynmanService
alpha = self._calculate_alpha(returns_buffer)
state["alpha_coefficient"] = alpha

# In Risk Manager
if alpha <= 2.0:
    approved_size = 0.0  # VETO
```

## 8. Validation & Robustness

### 8.1 Known Issues

**Issue 1**: **Small samples** ($n < 30$)

- Hill estimate very noisy
- **Mitigation**: Default to $\alpha = 3.0$ (Gaussian)

**Issue 2**: **Non-stationary** returns (regime shifts)

- $\alpha$ changes over time
- **Mitigation**: Use rolling window (100-252 bars)

**Issue 3**: **Discretization** effects

- Price tick sizes limit resolution
- **Mitigation**: Use log returns, not price levels

### 8.2 Diagnostic Plots

**Hill Plot**: $\hat{\alpha}(k)$ vs $k$

- Stable region → good estimate
- Monotonic drift → model mismatch

**QQ Plot**: Empirical vs Pareto quantiles

- Straight line → good fit
- Curvature → non-Pareto tails

## 9. Theoretical Justification

### 9.1 Why Heavy Tails Matter

**Gaussian Assumption**:
$$
P(X > x) \sim e^{-x^2/2\sigma^2}
$$

- Tail decays **exponentially fast**
- $P(X > 4\sigma) \approx 0.00003$ (1 in 30,000)

**Reality (Lévy Stable, $\alpha = 1.5$)**:
$$
P(X > x) \sim x^{-1.5}
$$

- Tail decays as **power law**
- $P(X > 4\sigma) \approx 0.03$ (1 in 33)

**Result**: Gaussian underestimates tail events by **1000x**.

### 9.2 Why $\alpha = 2.0$ is Critical

**Theorem (Generalized Central Limit)**:

- $\alpha > 2$: Sum of i.i.d. → Gaussian (CLT applies)
- $\alpha \leq 2$: Sum → Lévy Stable (infinite variance)

**Trading Implication**: Below $\alpha = 2$, **diversification fails**. Correlations break down, portfolio math is invalid.

## 10. Performance Characteristics

### Computational Complexity

- Sort: $O(n \log n)$
- Hill calc: $O(k)$
- **Total**: $O(n \log n)$ per window

### Latency

- 100 returns: ~50μs
- 252 returns: ~100μs
- Negligible for real-time

## 11. Limitations & Future Work

### Current Limitations

- ❌ Assumes **Pareto tails** (may not hold for all assets)
- ❌ No **time-varying $\alpha$** (uses rolling window)
- ❌ Symmetric treatment (ignores skewness)

### Planned Enhancements

- [ ] **Pickands Estimator** (robust alternative)
- [ ] **Conditional $\alpha$** (GARCH-like dynamics)
- [ ] **Separate left/right tails** (asymmetric risk)

## 12. References

- Hill, B. M. (1975). "A Simple General Approach to Inference About the Tail of a Distribution"
- Embrechts, P., Klüppelberg, C., & Mikosch, T. (1997). "Modelling Extremal Events"
- Taleb, N. N. (2020). "Statistical Consequences of Fat Tails"
- Mandelbrot, B. (1963). "The Variation of Certain Speculative Prices" (original heavy-tail finance paper)

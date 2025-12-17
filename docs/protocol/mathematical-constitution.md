# Curiosity Cottage Quantitative Protocol (CCQP) v3.0

**Mathematical Constitution & Intellectual Property**

## 1. The Physics Layer (Regime, Veto & Memory)

*Goal: Define the "State of the World," veto trades in infinite-variance regimes, and identify market memory.*

### 1.1. Heavy Tail Detection (The "Kill Switch")

We reject the assumption of Gaussian returns. We model the tail explicitly to prevent ruin.

**Formula: The Hill Estimator ($\alpha$)**
$$
\hat{\alpha} = \left( \frac{1}{k} \sum_{i=0}^{k-1} \ln \frac{X_{(n-i)}}{X_{(n-k)}} \right)^{-1}
$$

* **The Law:** If $\hat{\alpha} \le 2.0$, variance is infinite. **Trading Halted.**

### 1.2. Latent Regime Inference (HMM)

We model the market as a Markov process with hidden states $S_t \in \{ \text{LowVol, HighVol, Crisis} \}$.

### 1.3. Fractal Memory (The Hurst Exponent)

We measure the "Roughness" using Rescaled Range (R/S) Analysis.

**The Strategy Law:**

* **$0.5 < H \le 1.0$:** Persistent (Trend). **Active.**
* **$0.0 \le H < 0.5$:** Anti-Persistent (Mean Reversion). **Active.**

### 1.4. Quantum Dynamics (The Tunneling Probability)

*New in v3.0*

Classical physics dictates that a price cannot break a Resistance Level ($V$) if it lacks the Momentum ($E$). Quantum mechanics allows "Tunneling" through the barrier.

**Formula: The WKB Approximation**
$$
P_{tunnel} \approx \exp\left( -2 \int_{x_1}^{x_2} \sqrt{\frac{2m}{\hbar^2}(V(x) - E)} dx \right)
$$

* $V(x)$: The Potential Energy (Resistance/Support Level).
* $E$: The Kinetic Energy (Current Volatility/Momentum).
* **Application:** If $P_{tunnel} > \text{Threshold}$, execute **Breakout Trade** even if Momentum is low.

---

## 2. Input Processing (Data Hygiene)

*Goal: Preserve memory while ensuring statistical stationarity.*

### 2.0. Fractional Differentiation (FracDiff)

We use Fractional Differentiation to find the minimum $d$ required to satisfy the ADF test.

$$
\tilde{X}_t = \sum_{k=0}^{\infty} \omega_k X_{t-k}, \quad \omega_k = (-1)^k \binom{d}{k}
$$

---

## 3. The Trend Layer (State Estimation)

*Goal: De-noise price action to find the true "Kinematic State".*

### 3.1. The Kinematic Kalman Filter

**State Equation (Newtonian):**
$$
\mathbf{x}_k = \mathbf{F} \mathbf{x}_{k-1} + \mathbf{w}_k
$$

This assumes the "Price Particle" moves continuously.

### 3.2. The Quantum Harmonic Oscillator (QHO)

*New in v3.0*

For Mean Reversion regimes ($H < 0.5$), we model price as a particle trapped in a quadratic potential well (The "Fair Value" attractor).

**Formula: The Hamiltonian**
$$
\hat{H} = \frac{\hat{p}^2}{2m} + \frac{1}{2}m\omega^2\hat{x}^2
$$

**The Trading Law:**
Prices are stable only at discrete "Eigenstates" (Energy Levels).

$$
E_n = \hbar \omega \left(n + \frac{1}{2}\right)
$$

* If Price deviates from an Energy Level $E_n$ without sufficient energy to reach $E_{n+1}$, it **Must Revert** (Quantum Confinement).

---

## 4. The Signal Layer (Probabilistic Forecasting)

*Goal: Predict future price distribution.*

### 4.1. Chronos (Tokenized Forecasting)

Treating time series as a language modeling task ($P(x_{t+1}|x_{1:t})$).

### 4.2. Quantum Cognition (Interference)

*New in v3.0*

We reject the assumption that News Events ($A, B$) are commutative. The order of information affects market sentiment (Interference).

**Formula: The Interference Term**
$$
P(A \cup B) = P(A) + P(B) + 2\sqrt{P(A)P(B)} \cos \theta
$$

* $\theta$: The "Context Phase."
* **Application:** If $\cos \theta < 0$ (Destructive Interference), good news will be ignored. **Veto Long Signals.**

---

## 5. The Risk Layer (Sizing & Execution)

*Goal: Maximize geometric growth while strictly limiting ruin.*

### 5.1. Bayesian Expected Shortfall (BES) Sizing

$$
f^*_{bayes} = \lambda(\alpha) \cdot \frac{E[r_{posterior}] - r_f}{\text{BES}_{95\%}}
$$

* **$\lambda(\alpha)$**: The Physics Scalar (Heavy Tail Veto).

---

## Version History

- **v1.0**: Classical physics only (Kalman, Hill, Hurst)
* **v2.0**: Added HMM regime detection, Fractional Differentiation
* **v3.0**: **Quantum Extensions** - Tunneling, QHO, Quantum Cognition

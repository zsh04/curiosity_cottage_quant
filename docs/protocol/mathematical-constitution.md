# Curiosity Cottage Quantitative Protocol (CCQP) v2.1
**Mathematical Constitution & Intellectual Property**

## 1. The Physics Layer (Regime, Veto & Memory)
*Goal: Define the "State of the World," veto trades in infinite-variance regimes, and identify market memory.*

### 1.1. Heavy Tail Detection (The "Kill Switch")
We reject the assumption of Gaussian returns. We model the tail explicitly to prevent ruin.
**Formula: The Hill Estimator ($\alpha$)**
$$
\hat{\alpha} = \left( \frac{1}{k} \sum_{i=0}^{k-1} \ln \frac{X_{(n-i)}}{X_{(n-k)}} \right)^{-1}
$$
* $X_{(i)}$: Sorted absolute returns (tail events).
* $k$: Calibrated tail threshold.
* **The Law:** If $\hat{\alpha} \le 2.0$, variance is infinite. **Trading Halted.**

### 1.2. Latent Regime Inference (HMM)
We model the market as a Markov process with hidden states $S_t \in \{ \text{LowVol, HighVol, Crisis} \}$.
**Formula: Student-t Emission Probability**
$$
P(O_t | S_t = i) \sim t_{\nu}(\mu_i, \sigma_i)
$$

### 1.3. Fractal Memory (The Hurst Exponent)
We measure the "Roughness" and "Memory" of the time series to select the active strategy type using Rescaled Range (R/S) Analysis.
**Formula:**
$$
E[R(\tau)/S(\tau)] = C \cdot \tau^H
$$
We estimate $H$ as the slope of the log-log plot of $R/S$ vs. time lag $\tau$.

**The Strategy Law:**
* **$0.5 < H \le 1.0$ (Persistent):** Trend Following Mode. The past predicts the future. **Activate Kalman Trend Agent.**
* **$0.0 \le H < 0.5$ (Anti-Persistent):** Mean Reversion Mode. Price snaps back. **Activate Mean Reversion Agent.**
* **$H \approx 0.5$ (Random Walk):** Geometric Brownian Motion. **Cash / No Edge.**

---

## 2. Input Processing (Data Hygiene)
*Goal: Preserve memory while ensuring statistical stationarity.*

### 2.0. Fractional Differentiation (FracDiff)
Standard differencing ($d=1$) destroys trend memory. We use Fractional Differentiation to find the minimum $d$ required to satisfy the Augmented Dickey-Fuller (ADF) test (p < 0.05).

**Formula (Binomial Expansion):**
$$
\tilde{X}_t = \sum_{k=0}^{\infty} \omega_k X_{t-k}
$$
**Weights:**
$$
\omega_k = (-1)^k \binom{d}{k} = (-1)^k \frac{d(d-1)\dots(d-k+1)}{k!}
$$
* **Application:** All "Price" inputs to the Kalman Filter and Chronos must be Fractionally Differentiated first.

---

## 3. The Trend Layer (State Estimation)
*Goal: De-noise price action to find the true "Kinematic State" (Position, Velocity).*

### 3.1. The Kinematic Kalman Filter
We implement a discrete-time Kalman Filter configured for **Newtonian Kinematics**.

**State Equation (The Physics):**
$$
\mathbf{x}_k = \mathbf{F} \mathbf{x}_{k-1} + \mathbf{w}_k
$$
$$
\begin{bmatrix} p_k \\ v_k \\ a_k \end{bmatrix} = 
\begin{bmatrix} 1 & \Delta t & \frac{1}{2}\Delta t^2 \\ 0 & 1 & \Delta t \\ 0 & 0 & 1 \end{bmatrix} 
\begin{bmatrix} p_{k-1} \\ v_{k-1} \\ a_{k-1} \end{bmatrix} + \mathbf{w}_k
$$

**The Innovation:**
A "Buy" signal requires positive Velocity ($v > 0$) AND positive Acceleration ($a > 0$).

---

## 4. The Signal Layer (Probabilistic Forecasting)
*Goal: Predict future price distribution using Foundation Models.*

### 4.1. Chronos (Tokenized Forecasting)
We treat time series as a language modeling task.
**Formula:**
$$
P(x_{t+1:t+h} | x_{1:t}) \approx \prod_{i=1}^h P_{\theta}(\text{token}(x_{t+i}) | \text{token}(x_{1:t}))
$$
* **Signal:** We trade based on the **Entropy** of this distribution. High Entropy = High Uncertainty = Lower Size.

### 4.2. Macro Cointegration (The "Tide")
We monitor the spread between Equity ($S_t$) and Bond Yields ($B_t$).
**Formula: Ornstein-Uhlenbeck Process**
$$
dX_t = \kappa(\theta - X_t)dt + \sigma dW_t
$$
* If the spread $X_t$ diverges beyond $2\sigma$ (Z-Score), the **Macro Agent** signals a "Stress Regime."

---

## 5. The Risk Layer (Sizing & Execution)
*Goal: Maximize geometric growth while strictly limiting ruin.*

### 5.1. Bayesian Expected Shortfall (BES) Sizing
We explicitly reject variance-based sizing. We size based on the expected loss in the worst 5% of the *posterior* distribution.

**The Upgrade:**
$$
f^*_{bayes} = \lambda(\alpha) \cdot \frac{E[r_{posterior}] - r_f}{\text{BES}_{95\%}}
$$
* **$E[r_{posterior}]$**: Expected return from the Chronos/Kalman fusion.
* **$\text{BES}_{95\%}$**: Bayesian Expected Shortfall (Average tail loss of the posterior).
* **$\lambda(\alpha)$**: The **Physics Scalar**.
    * If $\alpha > 3.0$, $\lambda = 1.0$ (Full Size).
    * If $\alpha \le 2.1$, $\lambda \to 0$ (Zero Size).

### Context Visualization
To help you visualize how Hurst ($H$) interacts with Alpha ($\alpha$), consider this quadrant:
* **High Alpha ($>3$), High Hurst ($>0.6$):** The "Goldilocks" Zone. Strong Trend, Low Crash Risk. (Max Size Long).
* **High Alpha ($>3$), Low Hurst ($<0.4$):** The "Range" Zone. Safe, but choppy. (Mean Reversion).
* **Low Alpha ($<2$), Any Hurst:** The "Death" Zone. It doesn't matter if it's trending or mean-reverting; the variance is infinite. (Cash).

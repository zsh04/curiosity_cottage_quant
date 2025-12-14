# Curiosity Cottage Quantitative Protocol (CCQP) v2.0
**Mathematical Constitution & Intellectual Property**

## 1. The Physics Layer (Regime & Veto)
*Goal: Define the "State of the World" and veto trades in infinite-variance regimes.*

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

---

## 2. The Trend Layer (State Estimation)
*Goal: De-noise price action to find the true "Kinematic State" (Position, Velocity).*

### 2.1. The Kinematic Kalman Filter
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

## 3. The Signal Layer (Probabilistic Forecasting)
*Goal: Predict future price distribution using Foundation Models.*

### 3.1. Chronos (Tokenized Forecasting)
We treat time series as a language modeling task.
**Formula:**
$$
P(x_{t+1:t+h} | x_{1:t}) \approx \prod_{i=1}^h P_{\theta}(\text{token}(x_{t+i}) | \text{token}(x_{1:t}))
$$
* **Signal:** We trade based on the **Entropy** of this distribution. High Entropy = High Uncertainty = Lower Size.

### 3.2. Macro Cointegration (The "Tide")
We monitor the spread between Equity ($S_t$) and Bond Yields ($B_t$).
**Formula: Ornstein-Uhlenbeck Process**
$$
dX_t = \kappa(\theta - X_t)dt + \sigma dW_t
$$
* If the spread $X_t$ diverges beyond $2\sigma$ (Z-Score), the **Macro Agent** signals a "Stress Regime."

---

## 4. The Risk Layer (Sizing & Execution)
*Goal: Maximize geometric growth while strictly limiting ruin.*

### 4.1. ES-Constrained Fractional Kelly
We upgrade the standard Kelly formula ($f^*$) to account for fat tails.

**The Upgrade:**
$$
f^*_{robust} = \lambda(\alpha) \cdot \frac{\mu - r_f}{\text{ES}_{95\%}}
$$
* **$\text{ES}_{95\%}$**: Expected Shortfall (Average loss in the worst 5%).
* **$\lambda(\alpha)$**: The **Physics Scalar**.
    * If $\alpha > 3.0$, $\lambda = 1.0$ (Full Size).
    * If $\alpha \le 2.1$, $\lambda \to 0$ (Zero Size).

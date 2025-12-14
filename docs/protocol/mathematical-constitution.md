# Curiosity Cottage Quantitative Protocol (CCQP) v2.0
**Mathematical Constitution & Intellectual Property**

## 1. Capital Preservation Mandate (Survival First)
*Goal: Prevent ruin at all costs. "Ruin" is defined as any state that impairs future geometric compounding.*

### 1.1 The Ruin Barrier
* **Max Drawdown Limit:** **20%** of NAV.
    * If $DD_t > 0.20$, the fund effectively fails.
* **The Daily Stop:** **2.0%** of Equity.
    * If Daily Loss > 2.0%, the `ExecutionAgent` **MUST** liquidate all intraday positions and sleep for 24h.

---

## 2. The Physics Veto (Alpha Protocol)
*Goal: Vet trades based on the "State of the World" (Regime Detection).*
We reject the assumption of Gaussian returns. We model the tail explicitly using the **Hill Estimator**.

### 2.1 Heavy Tail Detection ($\alpha$)
$$
\hat{\alpha} = \left( \frac{1}{k} \sum_{i=0}^{k-1} \ln \frac{X_{(n-i)}}{X_{(n-k)}} \right)^{-1}
$$

**The Regime Table:**
| Regime | Tail Alpha ($\alpha$) | Leverage Cap | Action |
| :--- | :--- | :--- | :--- |
| **Gaussian** | $\alpha > 3.0$ | 1.0x (Cash) | Standard Trading |
| **Lévy Stable** | $2.0 < \alpha \le 3.0$ | 0.5x | Half-Kelly Sizing |
| **Critical** | $\alpha \le 2.0$ | **0.0x** | **HARD LIQUIDATION** |

---

## 3. Position Sizing (Coherent Risk)
*Goal: Sizing based on "Insurance" against 5-sigma events, not Volatility.*

### 3.1 Expected Shortfall Sizing
We explicitly do **NOT** use Volatility for sizing. We use **Expected Shortfall (ES)**.

**Formula:**
$$
\text{Size} = \frac{\text{Account Equity} \times \text{KellyFraction}}{\text{ES}_{95\%}}
$$

* **$\text{ES}_{95\%}$**: The average loss in the worst 5% of cases.
* This ensures that even if a tail event occurs, the dollar loss is bounded by our Kelly bet size.

---

## 4. The Kinematic Kalman Filter
*Goal: De-noise price action to find the true "Kinematic State" (Position, Velocity).*

**State Equation:**
$$
\begin{bmatrix} p_k \\ v_k \\ a_k \end{bmatrix} = 
\begin{bmatrix} 1 & \Delta t & \frac{1}{2}\Delta t^2 \\ 0 & 1 & \Delta t \\ 0 & 0 & 1 \end{bmatrix} 
\begin{bmatrix} p_{k-1} \\ v_{k-1} \\ a_{k-1} \end{bmatrix} + \mathbf{w}_k
$$
* **Signal:** Buy iff $v > 0$ AND $a > 0$.

# 📚 Project Glossary

## A. Mathematical Concepts

### Skew (Ratio)

**Definition:** The Ratio of Upside Volatility to Downside Volatility.
**Formula:** $Skew = \frac{q95 - q50}{q50 - q05}$
**Interpretation:**

- $> 1.0$: Upside Potential (Right Skew).
- $< 1.0$: Downside Risk (Left Skew/Crash Risk).
**Note:** This replaces the standard statistical skewness (3rd moment) for robustness in financial time-series.

### Sortino Ratio

**Definition:** A modification of the Sharpe Ratio that penalizes only downside volatility.
**Formula:** $Sortino = \frac{R_p - R_f}{\sigma_d}$
where $\sigma_d$ is the standard deviation of negative asset returns (Downside Deviation).

### Volatility Width

**Definition:** The normalized spread between the 95th and 5th percentiles.
**Formula:** $Width = \frac{q95 - q05}{P_t}$
**Usage:** Used to calculate dynamic position sizing and predatory slippage.

## B. System Components

### Chronos

The Recursive Neural Network (Amazon Chronos-Bolt) used for probabilistic forecasting.

### Backtest Engine (The Holodeck)

A vectorized simulation engine that replays historical data to validate strategies.

### Physics Veto

A risk governance mechanism that halts or reduces trading based on Heavy Tail detection (Hill Estimator).

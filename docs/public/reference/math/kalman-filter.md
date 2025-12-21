# Mathematical Specification: 3-State Kinematic Kalman Filter

**Location:** `app/lib/kalman/kinematic.py`  
**Purpose:** Optimal state estimation for price dynamics (Position, Velocity, Acceleration)  
**Model:** Constant Acceleration (Kinematic) Model

## 1. Mathematical Foundation

### 1.1 State Vector

The Kalman Filter estimates a **3-dimensional state vector**:

$$
\mathbf{x}_k = \begin{bmatrix} p_k \\ v_k \\ a_k \end{bmatrix}
$$

Where:

- $p_k$ = **Position** (Price at time $k$)
- $v_k$ = **Velocity** (Trend/Momentum)
- $a_k$ = **Acceleration** (Rate of change of momentum)

**Purpose**: Estimate the **true velocity** of price movement,filtering out market noise.

## 2. State-Space Model

### 2.1 State Transition (Process Model)

The state evolves according to **constant acceleration kinematics**:

$$
\mathbf{x}_k = \mathbf{F} \mathbf{x}_{k-1} + \mathbf{w}_k
$$

Where $\mathbf{F}$ is the **State Transition Matrix**:

$$
\mathbf{F} = \begin{bmatrix}
1 & \Delta t & \frac{1}{2} \Delta t^2 \\
0 & 1 & \Delta t \\
0 & 0 & 1
\end{bmatrix}
$$

**Kinematic Equations:**

- Position: $p_k = p_{k-1} + v_{k-1} \Delta t + \frac{1}{2} a_{k-1} \Delta t^2$
- Velocity: $v_k = v_{k-1} + a_{k-1} \Delta t$
- Acceleration: $a_k = a_{k-1}$ (constant acceleration assumption)

**Parameters:**

- $\Delta t$ = Time step (default: 1.0 for daily bars)

### 2.2 Observation Model

We **only observe price** (position), not velocity or acceleration:

$$
z_k = \mathbf{H} \mathbf{x}_k + \nu_k
$$

Where $\mathbf{H}$ is the **Observation Matrix**:

$$
\mathbf{H} = \begin{bmatrix} 1 & 0 & 0 \end{bmatrix}
$$

**Implication**: Velocity and acceleration are **latent variables** inferred from price movements.

## 3. Noise Modeling

### 3.1 Process Noise Covariance ($\mathbf{Q}$)

Represents uncertainty in the **dynamical model** (how the system evolves):

$$
\mathbf{Q} = q \cdot \mathbf{I}_3
$$

**Implementation:**

```python
self.Q = np.eye(3) * process_noise  # Simplified diagonal
```

**Default:** $q = 0.01$ (low process noise → trust the model)

> [!NOTE]
> The full continuous-time noise model is:
> $$
> \mathbf{Q}_{full} = q \begin{bmatrix}
> \frac{\Delta t^4}{4} & \frac{\Delta t^3}{2} & \frac{\Delta t^2}{2} \\
> \frac{\Delta t^3}{2} & \Delta t^2 & \Delta t \\
> \frac{\Delta t^2}{2} & \Delta t & 1
> \end{bmatrix}
> $$
> However, the simplified diagonal version is used for **numerical stability**.

### 3.2 Measurement Noise Covariance ($\mathbf{R}$)

Represents uncertainty in the **observations** (price measurement noise):

$$
\mathbf{R} = \begin{bmatrix} r \end{bmatrix}
$$

**Default:** $r = 1.0$ (moderate observation noise)

**Tuning Guideline:**

- $r \gg q$: Trust the model more → smoother estimates
- $r \ll q$: Trust measurements more → noisier, reactive estimates

## 4. Kalman Filter Recursion

The filter operates in two steps per time step: **Predict** and **Update**.

### 4.1 Predict Step

Project state and covariance forward in time:

$$
\hat{\mathbf{x}}_{k|k-1} = \mathbf{F} \hat{\mathbf{x}}_{k-1|k-1}
$$

$$
\mathbf{P}_{k|k-1} = \mathbf{F} \mathbf{P}_{k-1|k-1} \mathbf{F}^T + \mathbf{Q}
$$

**Notation:**

- $\hat{\mathbf{x}}_{k|k-1}$ = Predicted state at time $k$ given data up to $k-1$
- $\mathbf{P}_{k|k-1}$ = Predicted covariance

### 4.2 Update Step

Correct prediction using new measurement $z_k$:

#### Innovation (Measurement Residual)

$$
\mathbf{y}_k = z_k - \mathbf{H} \hat{\mathbf{x}}_{k|k-1}
$$

#### Innovation Covariance

$$
\mathbf{S}_k = \mathbf{H} \mathbf{P}_{k|k-1} \mathbf{H}^T + \mathbf{R}
$$

#### Kalman Gain

$$
\mathbf{K}_k = \mathbf{P}_{k|k-1} \mathbf{H}^T \mathbf{S}_k^{-1}
$$

**Interpretation**: $\mathbf{K}_k$ balances **model prediction** vs **new measurement**.

#### State Update

$$
\hat{\mathbf{x}}_{k|k} = \hat{\mathbf{x}}_{k|k-1} + \mathbf{K}_k \mathbf{y}_k
$$

#### Covariance Update

$$
\mathbf{P}_{k|k} = (\mathbf{I} - \mathbf{K}_k \mathbf{H}) \mathbf{P}_{k|k-1}
$$

## 5. Intelligent Initialization

**Challenge**: Cold start with zero velocity/acceleration is inaccurate.

**Solution**: Use first 3 measurements to estimate initial dynamics via **finite differences**.

### 5.1 Initial Velocity Estimate

Using **central difference** for better accuracy:

$$
\hat{v}_0 = \frac{p_2 - p_0}{2 \Delta t}
$$

### 5.2 Initial Acceleration Estimate

Using **second-order finite difference**:

$$
\hat{a}_0 = \frac{p_2 - 2p_1 + p_0}{\Delta t^2}
$$

**Implementation:**

```python
if len(init_buffer) < 3:
    return StateEstimate(measurement, 0.0, 0.0, P)

p0, p1, p2 = init_buffer
v0 = (p2 - p0) / (2 * dt)
a0 = (p2 - 2*p1 + p0) / (dt**2)
self.x = np.array([measurement, v0, a0])
```

**Result**: Filter begins with **realistic dynamics** instead of zero assumptions.

## 6. Output Schema

### StateEstimate (Dataclass)

```python
@dataclass
class StateEstimate:
    position: float       # Filtered price
    velocity: float       # Estimated trend ($/period)
    acceleration: float   # Momentum ($/period²)
    covariance: np.ndarray  # 3x3 uncertainty matrix
```

**Usage:**

```python
kf = KinematicKalmanFilter(dt=1.0)
for price in prices:
    state = kf.update(price)
    print(f"Trend: {state.velocity:.4f}")
```

## 7. Parameter Selection Guidelines

| Parameter | Symbol | Default | Effect |
|-----------|--------|---------|--------|
| Time Step | $\Delta t$ | 1.0 | Matches bar frequency (1 = daily) |
| Process Noise | $q$ | 0.01 | Higher → more reactive to changes |
| Measurement Noise | $r$ | 1.0 | Higher → smoother, less reactive |

### 7.1 Tuning Strategy

**For noisy, volatile assets** (e.g., crypto):

- Increase $r$ (measurement noise) to 2.0-5.0
- Keep $q$ low (0.01-0.05)
- Effect: Smoother velocity estimates, less whipsaw

**For trending, low-noise assets** (e.g., indices):

- Decrease $r$ to 0.5-1.0
- Increase $q$ slightly (0.05-0.1)
- Effect: More responsive to trend changes

## 8. Theoretical Properties

### 8.1 Optimality

The Kalman Filter is **BLUE** (Best Linear Unbiased Estimator) under assumptions:

1. Process noise $\mathbf{w}_k \sim \mathcal{N}(0, \mathbf{Q})$
2. Measurement noise $\nu_k \sim \mathcal{N}(0, \mathbf{R})$
3. Noises are uncorrelated
4. Linear dynamics

**Consequence**: For Gaussian noise, this is the **optimal** filter.

### 8.2 Stability

The filter is **asymptotically stable** if:

- $(\mathbf{F}, \mathbf{H})$ is **observable** ✓ (we observe position, can infer velocity)
- $(\mathbf{F}, \mathbf{Q}^{1/2})$ is **controllable** ✓

**Result**: Covariance $\mathbf{P}_k$ converges to steady-state.

## 9. Integration Points

### 9.1 Used By

- `KalmanMomentumStrategy` - Trend following based on velocity
- `PhysicsService` (legacy) - Kinematic calculations
- `FeynmanService` - Real-time physics state estimation

### 9.2 Telemetry

- `cc.physics.velocity` - Exported to metrics
- `cc.physics.acceleration` - Exported to metrics

## 10. Performance Characteristics

### Computational Complexity

- **Per update**: $O(n^3)$ for $n \times n$ covariance (here $n=3$)
- **Actual**: ~27 FLOPs per update (fixed size)
- **Latency**: <0.1ms per update

### Memory

- State: 3 floats + 3x3 matrix = 45 bytes
- Negligible for modern systems

## 11. Limitations & Assumptions

### Assumptions

1. **Constant Acceleration**: True velocity changes smoothly, not in jumps
2. **Gaussian Noise**: Invalidated during market crashes (heavy tails)
3. **Linear Dynamics**: No regime switches modeled

### Known Failure Modes

- **Flash Crashes**: Sudden jumps violate process model
- **Gaps**: Overnight gaps look like huge accelerations
- **Regime Changes**: Mean reversion ↔ Trending not captured

### Mitigations

- **Physics Veto**: Don't trade on Kalman signals during Critical regime ($\alpha < 2.0$)
- **Adaptive Noise**: Could modulate $q, r$ based on volatility (future enhancement)

## 12. References

- Kalman, R. E. (1960). "A New Approach to Linear Filtering and Prediction Problems"
- Bar-Shalom, Y. (2001). "Estimation with Applications to Tracking and Navigation"
- Welch & Bishop (2006). "An Introduction to the Kalman Filter" (UNC-CH TR)

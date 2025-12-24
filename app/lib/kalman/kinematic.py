import numpy as np
from dataclasses import dataclass


@dataclass
class StateEstimate:
    position: float
    velocity: float
    acceleration: float
    covariance: np.ndarray


class KinematicKalmanFilter:
    """3-state Extended Kalman Filter for price kinematics (position, velocity, acceleration).

        Estimates the "true" velocity and acceleration of price movements by filtering out
        market noise. Foundation for physics-based regime detection and trend following.

        **State Vector** (x):
        ```
        x = [position, velocity, acceleration]^T
          = [price, trend, momentum]^T
        ```

        **State Transition** (constant acceleration model):

    ```
        x_k = x_{k-1} + v *  dt + 0.5 * a * dt^2
        v_k = v_{k-1} + a * dt
        a_k = a_{k-1}  (assumed constant between observations)
        ```

        **Observation Model**:
        - Only price is observed directly (H = [1, 0, 0])
        - Velocity and acceleration are latent (inferred)

        **Smart Initialization** (3-sample warmup):
        - Uses finite differences on first 3 measurements
        - v0 = (p2 - p0) / (2*dt) (central difference)
        - a0 = (p2 - 2*p1 + p0) / dt^2 (second-order difference)
        - Prevents cold-start bias

        **Adaptive Noise Scaling**:
        - R_adaptive = R * (1 + volatility_factor^2)
        - Increases measurement noise during high volatility
        - Makes filter "stiffer" to resist whipsaw from Lévy flights

       Attributes:
            dt: Time step between observations (default: 1.0)
            F: State transition matrix (3x3)
            H: Observation matrix (1x3)
            Q: Process noise covariance (3x3)
            R: Measurement noise covariance (1x1)
            P: Error covariance matrix (3x3)
            x: State estimate vector (3,)

        Example:
            >>> kf = KinematicKalmanFilter(dt=1.0, process_noise=0.01)
            >>> state = kf.update(measurement=150.25, volatility_factor=0.5)
            >>> print(state.velocity, state.acceleration)
    """

    def __init__(
        self,
        dt: float = 1.0,
        process_noise: float = 0.01,
        measurement_noise: float = 1.0,
    ):
        self.dt = dt

        # State Transition Matrix (F)
        # x_k = x_{k-1} + v_{k-1}*dt + 0.5*a_{k-1}*dt^2
        # v_k = v_{k-1} + a_{k-1}*dt
        # a_k = a_{k-1}
        self.F = np.array([[1, dt, 0.5 * dt**2], [0, 1, dt], [0, 0, 1]])

        # Observation Matrix (H)
        # We only observe Price (Position)
        self.H = np.array([[1, 0, 0]])

        # Process Noise Covariance (Q)
        # Assume noise enters primarily through acceleration (the highest order term)
        # discrete noise model for constant acceleration
        q = process_noise
        dt2 = dt**2
        dt3 = dt**3
        dt4 = dt**4
        # self.Q = q * np.array([
        #     [dt4/4, dt3/2, dt2/2],
        #     [dt3/2, dt2,   dt],
        #     [dt2/2, dt,    1]
        # ])
        # Simplified diagonal noise for robust stability
        self.Q = np.eye(3) * process_noise

        # Measurement Noise Covariance (R)
        self.R = np.array([[measurement_noise]])

        # Initial Covariance (P)
        self.P = np.eye(3) * 100.0

        # Initial State (x)
        self.x = np.zeros(3)
        self.initialized = False

        # Initialization buffer for intelligent warmup
        self.init_buffer = []
        self.init_buffer_size = 3  # Use 3 measurements for initial estimates

    def update(
        self, measurement: float, volatility_factor: float = 0.0
    ) -> StateEstimate:
        """
        Performs one step of Predict-Update cycle.

        Args:
            measurement (float): The observed price.

        Returns:
            StateEstimate: The posterior estimate of Price, Velocity, Accel.
        """
        # SMART INITIALIZATION: Use first 3 measurements to estimate initial dynamics
        if not self.initialized:
            self.init_buffer.append(measurement)

            if len(self.init_buffer) < self.init_buffer_size:
                # Not enough data yet, return current measurement with zero dynamics
                self.x = np.array([measurement, 0.0, 0.0])
                return StateEstimate(self.x[0], self.x[1], self.x[2], self.P)

            # We have 3 measurements: p0, p1, p2
            # Estimate initial velocity from finite differences
            p0, p1, p2 = self.init_buffer

            # Velocity estimate: (p2 - p0) / (2 * dt)
            # Using central difference for better accuracy
            dt = self.dt
            v0 = (p2 - p0) / (2 * dt)

            # Acceleration estimate: (p2 - 2*p1 + p0) / dt^2
            # Second-order finite difference
            a0 = (p2 - 2 * p1 + p0) / (dt**2)

            # Initialize state with estimated dynamics
            self.x = np.array([measurement, v0, a0])
            self.initialized = True

            # Clear buffer
            self.init_buffer = []

            return StateEstimate(self.x[0], self.x[1], self.x[2], self.P)

        # --- Predict Step ---
        # x_pred = F * x_prev
        x_pred = self.F @ self.x

        # P_pred = F * P_prev * F^T + Q
        P_pred = self.F @ self.P @ self.F.T + self.Q

        # --- Update Step ---
        # Innovation (y) = z - H * x_pred
        y = measurement - self.H @ x_pred

        # Adaptive Noise Scaling (Phase 33.1)
        # If volatility is high, increase measurement noise (R) to trust the model more (stiffer filter)
        # mitigating "whipsaw" from non-Gaussian noise (Levy Flights).
        vol_factor = max(0.0, volatility_factor)
        R_adaptive = self.R * (1.0 + vol_factor**2)

        # Innovation Covariance (S) = H * P_pred * H^T + R_adaptive
        S = self.H @ P_pred @ self.H.T + R_adaptive

        # Kalman Gain (K) = P_pred * H^T * inv(S)
        K = P_pred @ self.H.T @ np.linalg.inv(S)

        # x_new = x_pred + K * y
        self.x = x_pred + (K @ y)  # Flatten if necessary, but dot usually handles it

        # P_new = (I - K * H) * P_pred
        I = np.eye(3)
        self.P = (I - K @ self.H) @ P_pred

        return StateEstimate(
            position=float(self.x[0]),
            velocity=float(self.x[1]),
            acceleration=float(self.x[2]),
            covariance=self.P,
        )

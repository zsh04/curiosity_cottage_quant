"""
Kinematic State Estimation.
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple


@dataclass
class KinematicState:
    position: float
    velocity: float
    acceleration: float


class KinematicKalmanFilter:
    """
    Discrete-time Kalman Filter configured for Newtonian Kinematics (Constant Acceleration Model).
    State vector x = [p, v, a].T
    """

    def __init__(
        self,
        dt: float = 1.0,
        process_noise: float = 0.01,
        measurement_noise: float = 1.0,
    ):
        self.dt = dt

        # State Transition Matrix (F)
        # p_k = p_{k-1} + v_{k-1}*dt + 0.5*a_{k-1}*dt^2
        # v_k = v_{k-1} + a_{k-1}*dt
        # a_k = a_{k-1}
        self.F = np.array([[1.0, dt, 0.5 * dt**2], [0.0, 1.0, dt], [0.0, 0.0, 1.0]])

        # Observation Matrix (H) - We only observe Position (Price)
        self.H = np.array([[1.0, 0.0, 0.0]])

        # Process Noise Covariance (Q)
        # Assumes variance in acceleration (Jerk) drives the system
        q = process_noise
        self.Q = (
            np.array(
                [
                    [0.25 * dt**4, 0.5 * dt**3, 0.5 * dt**2],
                    [0.5 * dt**3, dt**2, dt],
                    [0.5 * dt**2, dt, 1.0],
                ]
            )
            * q
        )

        # Measurement Noise Covariance (R)
        self.R = np.array([[measurement_noise]])

        # Initial State Covariance (P)
        self.P = np.eye(3) * 100.0

        # Initial State (x)
        self.x = np.zeros(3)

    def initialize(self, initial_price: float):
        """Set initial state based on first observation."""
        self.x = np.array([initial_price, 0.0, 0.0])

    def update(self, measurement: float) -> KinematicState:
        """
        Perform one Predict-Update cycle.
        Returns the posterior state estimate.
        """
        # 1. Predict
        x_pred = self.F @ self.x
        P_pred = self.F @ self.P @ self.F.T + self.Q

        # 2. Update
        # Innovation (Residual)
        z = np.array([measurement])
        y = z - self.H @ x_pred

        # Innovation Covariance
        S = self.H @ P_pred @ self.H.T + self.R

        # Kalman Gain
        K = P_pred @ self.H.T @ np.linalg.inv(S)

        # Posterior State
        self.x = x_pred + K @ y

        # Posterior Covariance
        I = np.eye(self.F.shape[0])
        self.P = (I - K @ self.H) @ P_pred

        return KinematicState(
            position=float(self.x[0]),
            velocity=float(self.x[1]),
            acceleration=float(self.x[2]),
        )

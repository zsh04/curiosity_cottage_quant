import pytest
import numpy as np
from app.lib.kalman.kinematic import KinematicKalmanFilter


class TestKinematicKalmanFilter:
    def test_initialization(self):
        kf = KinematicKalmanFilter()
        assert not kf.initialized

        # Warmup requires 3 observations
        kf.update(100.0)
        kf.update(101.0)
        est = kf.update(102.0)
        assert kf.initialized
        assert est.position == 102.0
        assert est.velocity == 1.0
        assert est.acceleration == 0.0

    def test_constant_velocity_convergence(self):
        """
        Feed a trajectory with constant velocity 1.0.
        Position: 100, 101, 102, ...
        Filter should estimate Velocity ~ 1.0 after settling.
        """
        kf = KinematicKalmanFilter(dt=1.0, process_noise=0.01, measurement_noise=1.0)

        # Simulate 20 steps
        true_velocity = 1.0
        start_pos = 100.0
        positions = [start_pos + i * true_velocity for i in range(20)]

        estimates = []
        for p in positions:
            est = kf.update(p)
            estimates.append(est)

        final_est = estimates[-1]

        # Check convergence
        # Velocity should be close to 1.0
        assert abs(final_est.velocity - true_velocity) < 0.2, (
            f"Velocity did not converge. Got {final_est.velocity}"
        )

        # Position should be close to measurement
        assert abs(final_est.position - positions[-1]) < 0.5

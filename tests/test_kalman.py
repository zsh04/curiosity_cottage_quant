import pytest
import unittest
from app.lib.kalman import KinematicKalmanFilter


class TestKinematicKalmanFilter(unittest.TestCase):
    def test_constant_velocity(self):
        # Scenario: Object moves at constant velocity of 1.0
        # Position sequence: 0, 1, 2, 3, 4, 5
        kf = KinematicKalmanFilter(dt=1.0, process_noise=0.001, measurement_noise=0.1)
        kf.update(0.0)

        observations = [1.0, 2.0, 3.0, 4.0, 5.0]
        states = []
        for obs in observations:
            states.append(kf.update(obs))

        final_state = states[-1]

        # Check Position (Should be close to 5.0)
        self.assertAlmostEqual(final_state.position, 5.0, delta=0.5)

        # Check Velocity (Should be close to 1.0)
        self.assertAlmostEqual(final_state.velocity, 1.0, delta=0.5)

        # Check Acceleration (Should be close to 0.0)
        self.assertAlmostEqual(final_state.acceleration, 0.0, delta=0.5)

    def test_constant_acceleration(self):
        # Scenario: Object accelerates at 1.0
        # p = 0.5 * a * t^2
        # t=0, p=0
        # t=1, p=0.5
        # t=2, p=2.0
        # t=3, p=4.5

        kf = KinematicKalmanFilter(dt=1.0, process_noise=0.01, measurement_noise=0.01)
        kf.update(0.0)

        observations = [0.5, 2.0, 4.5, 8.0, 12.5]
        states = []
        for obs in observations:
            states.append(kf.update(obs))

        final_state = states[-1]

        # Check Acceleration (Should be close to 1.0)
        self.assertAlmostEqual(final_state.acceleration, 1.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()

import unittest
from app.core.health import SystemHealth


class TestSystemHealth(unittest.TestCase):
    def test_health_perfect(self):
        """
        Ideal conditions: 0 latency, 0 jitter, empty queue.
        Health should be 1.0.
        """
        sh = SystemHealth()
        # Mock history
        sh._latencies.append(0.0)
        # sh._jitter_history? Jitter is calculated from latencies.

        score = sh.get_health()
        self.assertEqual(score, 1.0)

    def test_health_degraded_latency(self):
        """
        High Latency (200ms) should degrade health below 0.999?
        """
        sh = SystemHealth()
        # Reset
        sh._latencies.clear()

        # Inject 200ms latency
        for _ in range(10):
            sh._latencies.append(0.200)

        score = sh.get_health()
        print(f"Health (200ms): {score}")

        self.assertLess(
            score, 0.999, "System did not flag degraded health due to latency"
        )

    def test_health_safe_latency(self):
        """
        Normal Latency (20ms).
        """
        sh = SystemHealth()
        sh._latencies.clear()

        for _ in range(10):
            sh._latencies.append(0.020)

        score = sh.get_health()
        print(f"Health (20ms): {score}")

        self.assertGreater(
            score, 0.999, "System flagged false positive on normal latency"
        )


if __name__ == "__main__":
    unittest.main()

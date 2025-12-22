import time
import psutil
import statistics
from collections import deque
from typing import Deque


class SystemHealth:
    """
    Law Zero: The Operational Health Tensor.
    Monitors physical integrity of the system.
    """

    MIN_HEALTH = 0.999

    def __init__(self, history_size: int = 100):
        self._latencies: Deque[float] = deque(maxlen=history_size)
        self._last_tick = time.perf_counter()

    def check_latency(self) -> float:
        """Measure time delta since last check."""
        now = time.perf_counter()
        delta = now - self._last_tick
        self._last_tick = now
        self._latencies.append(delta)
        return delta

    def check_jitter(self) -> float:
        """Calculate standard deviation of recent latencies."""
        if len(self._latencies) < 2:
            return 0.0
        return statistics.stdev(self._latencies)

    def check_memory(self) -> float:
        """Return memory usage fraction (0.0 to 1.0)."""
        return psutil.virtual_memory().percent / 100.0

    def check_queue_depth(self) -> int:
        """
        Mockable queue depth check.
        In a real scenario, this would check Redis/Internal queues.
        For now, returns 0 as we are in a backtest loop mostly.
        """
        # TODO: Connect to Redis if needed for depth check
        return 0

    def get_health(self) -> float:
        """
        Calculate H = 1.0 - (norm_latency + norm_jitter + norm_queue_depth)

        Normalization assumes:
        - Latency > 100ms is bad (0.1s)
        - Jitter > 50ms is bad (0.05s)
        - Queue Depth > 1000 is bad
        """
        # 1. Update Metrics
        lat = self.check_latency()  # current tick delta
        jit = self.check_jitter()
        # mem = self.check_memory() # Available for future use
        q_depth = self.check_queue_depth()

        # 2. Normalize
        # Latency Reference: 100ms (0.1s) -> 1.0 penalty check?
        # Let's say we want small penalties.
        # If latency is 1ms (0.001), penalty should be small.
        # If latency is 100ms, penalty should be significant.

        # Scaling factors (Tunable)
        NORM_LATENCY = 0.1  # 100ms
        NORM_JITTER = 0.05  # 50ms
        NORM_Q = 1000.0

        n_lat = min(1.0, lat / NORM_LATENCY) if NORM_LATENCY > 0 else 0
        n_jit = min(1.0, jit / NORM_JITTER) if NORM_JITTER > 0 else 0
        n_q = min(1.0, q_depth / NORM_Q) if NORM_Q > 0 else 0

        # Weighting
        # If Latency > 100ms, we want H < 0.999.
        # So 1.0 (normalized) should equate to > 0.001 penalty.
        # Let's say if Latency is 100ms, penalty is 0.002.

        w_lat = 0.002
        w_jit = 0.002
        w_q = 0.002

        total_penalty = (n_lat * w_lat) + (n_jit * w_jit) + (n_q * w_q)

        health = 1.0 - total_penalty
        return health

import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from app.lib.memory import FractalMemory
from app.strategies import ENABLED_STRATEGIES
import app.adapters.market  # Should verify adapters still exist


def test_fractal_memory():
    print("Testing FractalMemory...")
    # Create a synthetic random walk (non-stationary)
    np.random.seed(42)
    prices = np.cumsum(np.random.normal(size=100)) + 100

    # Test find_optimal_d
    d, diff_series = FractalMemory.find_optimal_d(prices)
    print(f"Optimal d: {d}")

    # Test transform
    transformed = FractalMemory.transform(prices)
    print(f"Transformed length: {len(transformed)}")

    assert len(transformed) > 0
    assert d >= 0.0 and d <= 1.0
    print("FractalMemory Tests Passed.")


def test_preservation():
    print("Testing Preservation...")
    # Check MoonPhase
    moon_phase_found = any("MoonPhase" in str(s) for s in ENABLED_STRATEGIES)
    print(f"MoonPhase Found: {moon_phase_found}")
    assert moon_phase_found

    print("Preservation Tests Passed.")


if __name__ == "__main__":
    try:
        test_fractal_memory()
        test_preservation()
        print("✅ Phase 38 Verification SUCCESS")
    except Exception as e:
        print(f"❌ Phase 38 Verification FAILED: {e}")
        sys.exit(1)

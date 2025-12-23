import sys
import os
import subprocess
from unittest.mock import MagicMock

# Fix path for integration check module resolution
sys.path.append(os.getcwd())

# Mocks for Integration Check (app.services.backtest)
sys.modules["faststream"] = MagicMock()
sys.modules["faststream.redis"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["redis.asyncio"] = MagicMock()
sys.modules["lancedb"] = MagicMock()
mock_lance_pydantic = MagicMock()


class MockLanceModel:
    pass


class MockVector:
    def __init__(self, dim=None):
        pass


mock_lance_pydantic.LanceModel = MockLanceModel
mock_lance_pydantic.Vector = MockVector
sys.modules["lancedb.pydantic"] = mock_lance_pydantic
sys.modules["lancedb.pydantic"] = mock_lance_pydantic
sys.modules["transformers"] = MagicMock()
mock_pa = MagicMock()
mock_pa.__version__ = "14.0.0"
# Use MagicMock class as DataType so isinstance(mock_obj, DataType) is True
mock_pa.DataType = MagicMock
sys.modules["pyarrow"] = mock_pa
sys.modules["pyarrow.compute"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()


def run_unit_tests():
    print(">>> Running Phase 37 Unit Tests via Pytest...")

    test_files = [
        "tests/unit/test_boyd_covariance.py",
        "tests/unit/test_feynman_entropy.py",
        "tests/unit/test_execution_slippage.py",
    ]

    try:
        cmd = ["pytest"] + test_files
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        print(">>> Pytest Validation FAILED.")
        return False
    except Exception as e:
        print(f"FAILED to run pytest: {e}")
        return False


def verify_backtest_integration():
    print("\n>>> Verifying Backtest Engine Integration...")
    try:
        import app.services.backtest as bt_service

        # Patch internals
        bt_service.TimeSeriesForecaster = MagicMock()
        bt_service.SystemHealth = MagicMock()
        bt_service.BacktestDAL = MagicMock()
        bt_service.Redis = MagicMock()

        # Mock class for Boyd
        mock_boyd = MagicMock()
        bt_service.BoydAgent = MagicMock(return_value=mock_boyd)

        # Init Engine
        print("    Initializing BacktestEngine...")
        engine = bt_service.BacktestEngine("2024-01-01", "2024-01-02")

        if hasattr(engine, "boyd"):
            if engine.boyd is not None:
                print("    SUCCESS: BacktestEngine.boyd is initialized.")
                return True
            else:
                print("    FAILURE: BacktestEngine.boyd found but is None.")
                return False
        else:
            print("    FAILURE: BacktestEngine missing 'boyd' attribute.")
            return False

    except Exception as e:
        print(f"    FAILURE during Backtest Engine Init Check: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    tests_ok = run_unit_tests()
    if tests_ok:
        integration_ok = verify_backtest_integration()
        if integration_ok:
            print("\n✅ PHASE 37 VERIFICATION COMPLETE: ALL SYSTEMS GO.")
            sys.exit(0)
        else:
            print("\n❌ PHASE 37 VERIFICATION FAILED (Integration).")
            sys.exit(1)
    else:
        print("\n❌ PHASE 37 VERIFICATION FAILED (Unit Tests).")
        sys.exit(1)

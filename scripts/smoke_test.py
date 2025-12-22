"""
Pre-Flight Smoke Test for Curiosity Cottage V2.
Validates all critical subsystems before launch.
"""

import sys
import pandas as pd
from sqlalchemy import text
from app.dal.database import SessionLocal
from app.services.feynman_bridge import FeynmanBridge
from app.adapters.chronos import ChronosAdapter
from app.adapters.sentiment import SentimentAdapter
from app.strategies.lstm import LSTMPredictionStrategy


def print_header():
    """Print test header."""
    print("\n" + "=" * 60)
    print("🚀 CURIOSITY COTTAGE V2 - PRE-FLIGHT SMOKE TEST")
    print("=" * 60 + "\n")


def test_database():
    """Test 1: Database Connectivity."""
    print("🔍 Test 1: Database Connectivity...")
    try:
        db = SessionLocal()
        try:
            # Try to query market_ticks table
            result = db.execute(text("SELECT 1 FROM market_ticks LIMIT 1"))
            result.fetchone()
            print("   ✅ Database: Connected")
            print("   ✅ Table 'market_ticks': Accessible\n")
            return True
        finally:
            db.close()
    except Exception as e:
        print(f"   ❌ Database: FAILED - {e}\n")
        return False


def test_chronos():
    """Test 2: Chronos Forecasting Service."""
    print("🔍 Test 2: Chronos Forecasting Service...")
    try:
        chronos = ChronosAdapter()

        # Mock prediction with dummy data
        dummy_history = [100.0, 101.0, 102.0, 103.0, 102.5]
        result = chronos.forecast(dummy_history, horizon=5)

        if result and "predictions" in result:
            print(f"   ✅ Chronos: Responding")
            print(f"   ✅ Sample Forecast: {result['predictions'][:3]}...\n")
            return True
        else:
            print("   ❌ Chronos: Invalid response format\n")
            return False

    except Exception as e:
        print(f"   ❌ Chronos: FAILED - {e}\n")
        return False


def test_finbert():
    """Test 3: FinBERT Sentiment Analysis."""
    print("🔍 Test 3: FinBERT Sentiment Service...")
    try:
        finbert = SentimentAdapter()

        # Mock sentiment analysis
        test_text = "The market shows strong bullish momentum."
        result = finbert.analyze(test_text)

        if result and "label" in result and "score" in result:
            print(f"   ✅ FinBERT: Responding")
            print(f"   ✅ Sample Analysis: {result['label']} ({result['score']:.2f})\n")
            return True
        else:
            print("   ❌ FinBERT: Invalid response format\n")
            return False

    except Exception as e:
        print(f"   ❌ FinBERT: FAILED - {e}\n")
        return False


def test_physics():
    """Test 4: Physics Service (Kinematics)."""
    print("🔍 Test 4: Physics Service...")
    try:
        physics = FeynmanBridge()

        # Test kinematics calculation
        dummy_prices = [100.0, 101.0, 102.0, 103.0, 102.5, 104.0]
        kinematics = physics.calculate_kinematics(dummy_prices)

        if (
            kinematics
            and "velocity" in kinematics
            and kinematics["velocity"] is not None
        ):
            print(f"   ✅ Kinematics: Calculated")
            print(f"   ✅ Velocity: {kinematics['velocity']:.4f}")
            print(f"   ✅ Acceleration: {kinematics['acceleration']:.4f}\n")
            return True
        else:
            print("   ❌ Physics: Invalid kinematics output\n")
            return False

    except Exception as e:
        print(f"   ❌ Physics: FAILED - {e}\n")
        return False


def test_strategy():
    """Test 5: Strategy Execution (LSTM)."""
    print("🔍 Test 5: Strategy Execution...")
    try:
        strategy = LSTMPredictionStrategy()

        # Create dummy DataFrame
        dummy_data = pd.DataFrame(
            {"close": [100, 101, 102, 103, 102.5, 104, 105, 104.5, 106, 107]}
        )

        signal = strategy.calculate_signal(dummy_data)

        if isinstance(signal, (int, float)) and -1 <= signal <= 1:
            print(f"   ✅ Strategy: Executed")
            print(f"   ✅ Signal: {signal:.4f} (valid range)\n")
            return True
        else:
            print(
                f"   ❌ Strategy: Invalid signal {signal} (must be float in [-1, 1])\n"
            )
            return False

    except Exception as e:
        print(f"   ❌ Strategy: FAILED - {e}\n")
        return False


def main():
    """Run all smoke tests."""
    print_header()

    results = {
        "Database": test_database(),
        "Chronos": test_chronos(),
        "FinBERT": test_finbert(),
        "Physics": test_physics(),
        "Strategy": test_strategy(),
    }

    # Print Summary
    print("=" * 60)
    print("📊 SMOKE TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:<20} {status}")

    print("=" * 60)

    # Final Verdict
    all_passed = all(results.values())

    if all_passed:
        print("\n🟢 ✅ ALL SYSTEMS GO - READY FOR LAUNCH\n")
        sys.exit(0)
    else:
        failed_tests = [name for name, passed in results.items() if not passed]
        print(f"\n🔴 ❌ FAILURE: {', '.join(failed_tests)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

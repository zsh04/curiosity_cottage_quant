#!/usr/bin/env python3
"""
Chronos Forecasting Verification Script
Tests the cc_engine -> cc_chronos microservice integration.
"""

import sys
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.chronos import ChronosAdapter


def generate_sine_wave(length: int = 50, base_price: float = 100.0) -> list:
    """
    Generate synthetic sine wave price data.

    Args:
        length: Number of data points
        base_price: Base price level

    Returns:
        List of prices following a sine wave pattern
    """
    x = np.linspace(0, 4 * np.pi, length)
    amplitude = 10.0
    prices = base_price + amplitude * np.sin(x)
    return prices.tolist()


def verify_chronos():
    """
    Main verification function.
    Tests Chronos adapter with synthetic data.
    """
    print("🧪 CHRONOS VERIFICATION TEST")
    print("=" * 60)

    # Step 1: Generate synthetic data
    print("\n1️⃣  Generating synthetic sine wave (50 points)...")
    prices = generate_sine_wave(length=50, base_price=100.0)
    current_price = prices[-1]
    print(f"   Current Price: ${current_price:.2f}")

    # Step 2: Initialize adapter
    print("\n2️⃣  Initializing ChronosAdapter...")
    adapter = ChronosAdapter()

    # Step 3: Check health
    print("\n3️⃣  Checking Chronos service health...")
    if adapter.health_check():
        print("   ✅ Chronos service is healthy")
    else:
        print("   ❌ Chronos service unreachable")
        print("\n💡 TIP: Start cc_chronos with: docker-compose up -d cc_chronos")
        return False

    # Step 4: Generate forecast
    print("\n4️⃣  Requesting 10-step forecast...")
    forecast = adapter.predict(prices, horizon=10)

    # Step 5: Validate response
    print("\n5️⃣  Validating response...")
    if forecast is None:
        print("   ❌ CHRONOS DEAD: No response received")
        return False

    if not isinstance(forecast, dict):
        print("   ❌ Invalid response type")
        return False

    median = forecast.get("median", [])
    low = forecast.get("low", [])
    high = forecast.get("high", [])

    if not median:
        print("   ❌ Empty median forecast")
        return False

    # Step 6: Print results
    print("   ✅ Valid forecast received!")
    print(f"\n📊 FORECAST SUMMARY:")
    print(f"   Current Price:      ${current_price:.2f}")
    print(f"   Predicted (t+10):   ${median[-1]:.2f}")
    print(f"   Prediction Range:   ${low[-1]:.2f} - ${high[-1]:.2f}")

    # Step 7: Directional validation
    print(f"\n🧮 DIRECTIONAL ANALYSIS:")

    # Calculate recent trend from last 5 points
    recent_trend = prices[-1] - prices[-5]
    predicted_change = median[-1] - current_price

    print(
        f"   Recent Trend:       {'↗️ Up' if recent_trend > 0 else '↘️ Down'} ({recent_trend:+.2f})"
    )
    print(
        f"   Predicted Change:   {'↗️ Up' if predicted_change > 0 else '↘️ Down'} ({predicted_change:+.2f})"
    )

    # Sine wave is periodic, so we don't strictly validate direction
    # but we ensure the prediction is within a reasonable range
    price_range = max(prices) - min(prices)
    forecast_deviation = abs(median[-1] - current_price)

    if forecast_deviation < price_range * 2:  # Reasonable bounds
        print(f"   ✅ Forecast within reasonable bounds")
    else:
        print(f"   ⚠️  Large forecast deviation detected")

    # Success
    print("\n" + "=" * 60)
    print("✅ CHRONOS ALIVE: Prediction received and validated!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = verify_chronos()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

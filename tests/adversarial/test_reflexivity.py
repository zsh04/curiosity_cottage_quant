import sys
from unittest.mock import MagicMock

# MOCK FASTSTREAM & REDIS to prevent connection hangs
sys.modules["faststream"] = MagicMock()
sys.modules["faststream.redis"] = MagicMock()
sys.modules["redis.asyncio"] = MagicMock()
# MOCK HEAVY ML LIBS
sys.modules["transformers"] = MagicMock()
sys.modules["optimum"] = MagicMock()
sys.modules["optimum.onnxruntime"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()

import pytest
import numpy as np
from app.services.soros import SorosService
from app.agent.boyd import BoydAgent
from app.core.vectors import PhysicsVector, ReflexivityVector, OODAVector


class TestSystemReflexivity:
    """
    Phase 36.3: The Soros Loop (Reflexivity QA).
    Tests the system's ability to detect self-inflicted price moves (Reflexivity)
    and veto them in the OODA Loop.
    """

    def test_soros_reflexivity_calculation(self):
        """
        Scenario: The Bait.
        We inject a sequence of TRADES (Executions) and concurrent Price Moves
        that are perfectly correlated (Self-Driving Market).
        Soros should detect High Reflexivity.
        """
        soros = SorosService(window_size=20)

        # 1. Setup Correlated Data (Buying pushes price UP)
        # We simulate 10 trades
        base_price = 100.0
        soros.last_prices["BAIT"] = base_price  # Initialize to capture first delta

        for i in range(10):
            # We BUY 10 units + i (Varying volume to allow Correlation calc)
            # Higher Volume -> Higher Impact
            qty = 10.0 + float(i)
            soros.record_execution("BAIT", qty)

            # Price moves UP proportional to Volume (Impact)
            impact = qty * 0.1
            current_price = base_price + impact
            base_price = current_price  # Accumulate price

            # This triggers the specific delta calculation for the *previous* trade?
            # My logic in soros.py:
            # record_execution(qty) -> appends to my_volumes, appends 0.0 to price_deltas
            # calculate_reflexivity(price) -> updates last element of price_deltas with (price - last_price)

            # So sequence: Record -> Calculate
            vec = soros.calculate_reflexivity("BAIT", current_price)

            # Debug
            # print(f"Step {i}: Vol={qty}, Price={current_price}, Vector={vec}")

        # 2. Check Result
        # The last vector from the loop should be perfectly correlated
        # We don't need to call calculate again with arbitrary price, that ruins the last data point.
        final_vec = vec

        print(f"\nFinal Reflexivity Vector: {final_vec}")

        assert final_vec.reflexivity_index > 0.8, (
            f"Reflexivity Check Failed: {final_vec.reflexivity_index} <= 0.8"
        )
        assert final_vec.reflexivity_index <= 1.000001

    def test_boyd_ooda_veto(self):
        """
        Scenario: The Trap.
        Physics detects high momentum (looks like a breakout).
        BUT Reflexivity detects it's OUR volume driving it.
        Boyd must VETO (Low Urgency).
        """
        boyd = BoydAgent()

        # 1. High Momentum Physics (The Bait)
        physics = PhysicsVector(
            mass=1000.0,
            momentum=10.0,  # Huge Upward Velocity
            entropy=0.1,  # Low Entropy (Clean Trend)
            jerk=0.5,
            nash_dist=0.0,
            alpha_coefficient=2.5,
            price=150.0,
        )

        # 2. High Reflexivity (The Trap)
        reflexivity = ReflexivityVector(
            sentiment_delta=0.0,
            reflexivity_index=0.95,  # We did this.
        )

        # 3. Boyd's Decision
        ooda = boyd._calculate_ooda(physics, reflexivity)

        print(f"\nBoyd OODA Vector: {ooda}")

        # 4. Assert VETO (Urgency < 0.2)
        assert ooda.urgency_score < 0.2, (
            f"Boyd failed to Veto! Urgency {ooda.urgency_score} too high."
        )

    def test_boyd_ooda_chase(self):
        """
        Scenario: The Breakout (Real).
        High Momentum + LOW Reflexivity (Market is driving it, not us).
        Boyd should act with HIGH Urgency.
        """
        boyd = BoydAgent()

        physics = PhysicsVector(
            mass=1000.0,
            momentum=0.01,  # Moderate strong momentum (normalized)
            entropy=0.1,
            jerk=0.5,
            nash_dist=0.0,
            alpha_coefficient=2.5,
            price=150.0,
        )

        # Low Reflexivity
        reflexivity = ReflexivityVector(sentiment_delta=0.0, reflexivity_index=0.1)

        ooda = boyd._calculate_ooda(physics, reflexivity)

        print(f"\nBoyd Chase OODA: {ooda}")

        # Should be reasonably high (heuristic depends on scaling)
        # In my logic: p_score = min(1.0, 0.01 * 1000) = 10.0 -> 1.0.
        # base = 0.7 * 1.0 + ... = > 0.7
        # dampener = 1.0
        assert ooda.urgency_score > 0.5, (
            f"Boyd failed to Chase! Urgency {ooda.urgency_score} too low."
        )

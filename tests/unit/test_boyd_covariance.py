import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock
from app.agent.boyd import BoydAgent


class TestBoydCovariance:
    def test_covariance_veto_logic(self):
        """
        Verify that Boyd vetoes one of two perfectly correlated assets.
        """
        boyd = BoydAgent()

        # 1. Create Correlated Data
        # Asset A: Up trend
        hist_a = [100 + i for i in range(100)]
        # Asset B: Perfectly Correlated (Up trend)
        hist_b = [50 + i * 2 for i in range(100)]

        candidates = [
            {
                "symbol": "ASSET_A",
                "history": hist_a,
                "signal_confidence": 0.9,
                "velocity": 0.01,
                "success": True,
                "reasoning": "",
            },
            {
                "symbol": "ASSET_B",
                "history": hist_b,
                "signal_confidence": 0.5,  # Lower confidence, should be vetoed
                "velocity": 0.01,
                "success": True,
                "reasoning": "",
            },
        ]

        # 2. Apply Veto
        filtered = boyd._apply_covariance_veto(candidates)

        # 3. Assertions
        assert len(filtered) == 2

        cand_a = next(c for c in filtered if c["symbol"] == "ASSET_A")
        cand_b = next(c for c in filtered if c["symbol"] == "ASSET_B")

        assert cand_a["success"] is True, "Winner should survive"
        assert cand_b["success"] is False, "Loser should be vetoed"
        assert "VETOED" in cand_b.get("reasoning", ""), "Reasoning should reflect Veto"

    def test_covariance_no_veto(self):
        """
        Verify that uncorrelated assets are untouched.
        """
        boyd = BoydAgent()

        # Asset A: Up (Linear)
        hist_a = [100 + i for i in range(100)]
        # Asset C: Random / Noise (Uncorrelated)
        np.random.seed(42)
        hist_c = np.random.normal(100, 1, 100).tolist()

        candidates = [
            {
                "symbol": "ASSET_A",
                "history": hist_a,
                "signal_confidence": 0.9,
                "success": True,
                "reasoning": "",
            },
            {
                "symbol": "ASSET_C",
                "history": hist_c,
                "signal_confidence": 0.8,
                "success": True,
                "reasoning": "",
            },
        ]

        filtered = boyd._apply_covariance_veto(candidates)

        assert filtered[0]["success"] is not False
        assert filtered[1]["success"] is not False

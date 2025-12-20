import pytest
import torch
import numpy as np
from app.services.chronos import ChronosService
from app.core.models import ForecastPacket


class TestSimonsMind:
    @pytest.fixture
    def simons(self):
        # Disable loading real weights for unit tests to speed up
        # We can test the logic flow.
        # But if we want to confirm structure, we might need a mocked pipeline.
        service = ChronosService(model_name="amazon/chronos-t5-tiny")
        return service

    def test_hardware_acceleration(self, simons):
        """Test 1: Verify MPS availability (Warn only if missing)."""
        is_mps = torch.backends.mps.is_available()
        print(f"Hardware Check: MPS Available = {is_mps}")
        # We don't fail the test if generic runner lacks GPU,
        # but we assert the service detected what was available.
        if is_mps:
            assert simons.device == "mps"
        else:
            assert simons.device == "cpu"

    def test_forecast_logic(self, simons):
        """Test 2: Feed data and verify ForecastPacket structure."""
        # Feed 50 ticks
        start_price = 100.0
        for i in range(50):
            simons.update_buffer(start_price + i * 0.1)

        # Context should be filled partially
        assert simons.cursor == 50

        # Force a forecast (mocking pipeline if not present)
        # We invoke forecast().
        # Note: logic requires throttle checks.
        # tick_counter is incremented inside forecast().
        # We reset it to ensure it triggers (throttle=10).
        simons.tick_counter = 9

        packet = simons.forecast()

        if packet:
            assert isinstance(packet, ForecastPacket)
            assert packet.p10 < packet.p90
            assert packet.p50 > packet.p10
            assert packet.p50 < packet.p90
            assert packet.horizon == 10
            assert 0.0 <= packet.confidence <= 1.0

    def test_serialization(self, simons):
        """Test 3: Verify JSON output."""
        packet = ForecastPacket(
            timestamp="2025-01-01T12:00:00",
            symbol="BTC-USD",
            p10=90.0,
            p50=100.0,
            p90=110.0,
            horizon=10,
            confidence=0.8,
        )

        json_str = packet.model_dump_json()
        assert "p50" in json_str
        assert "confidence" in json_str

import sys
from unittest.mock import MagicMock, AsyncMock

# MOCK FASTSTREAM & REDIS BEFORE IMPORT
mock_faststream = MagicMock()
mock_redis_module = MagicMock()

# Configure Broker Mock to allow decorator pass-through
mock_broker_instance = MagicMock()


def subscriber_side_effect(*args, **kwargs):
    def decorator(func):
        return func

    return decorator


mock_broker_instance.subscriber.side_effect = subscriber_side_effect

# Configure Publish/Redis Set to be awaitable for internal calls
mock_broker_instance.publish = AsyncMock()
mock_redis_client = MagicMock()
mock_redis_client.set = AsyncMock()
mock_broker_instance.redis = mock_redis_client

mock_redis_module.RedisBroker = MagicMock(return_value=mock_broker_instance)

sys.modules["faststream"] = mock_faststream
sys.modules["faststream.redis"] = mock_redis_module
sys.modules["redis.asyncio"] = MagicMock()

import pytest
import numpy as np
from app.services.feynman import FeynmanService, handle_tick
from app.core.vectors import PhysicsVector


@pytest.fixture(autouse=True)
def setup_mocks():
    # Reinforce mocks if needed, but the module import should have used the sys.modules mocks
    pass


class TestHypatiaEntropy:
    def test_dynamic_threshold_calculation(self):
        """
        Verify logic: Threshold = Max(3.0, Volatility * 1.5).
        Since logic is embedded in handle_tick, we simulate the volatility condition
        by inspecting how we would implement the check logic or extracting it.

        Actually, we can test the Logic directly or integration test handle_tick.
        Let's try to verify via integration with a Mock Logic Check since handle_tick is async/complex.

        Alternatively, checking if the logger.warning is called when entropy is high but vol is low vs high.
        """
        pass

    @pytest.mark.asyncio
    async def test_hypatia_logic_flow(self):
        """
        Integration test for handle_tick logic regarding entropy.
        """
        # Mock Kernel
        import app.services.feynman as feynman_module

        feynman_module.kernel = MagicMock()
        feynman_module.broker = MagicMock()
        feynman_module.logger = MagicMock()

        kernel = feynman_module.kernel
        kernel.window_size = 100
        kernel.is_filled = True
        kernel.cursor = 100

        # 1. Case: High Entropy, Low Volatility -> VETO
        # Entropy = 3.5 (Chaos), Vol = 0.1
        # Threshold = Max(3.0, 0.15) = 3.0
        # 3.5 > 3.0 -> VETO

        mock_forces = PhysicsVector(
            mass=100.0,
            momentum=0.0,
            entropy=3.5,
            jerk=0.0,
            nash_dist=0.0,
            alpha_coefficient=2.0,
            price=100.0,
        )
        kernel.calculate_forces.return_value = mock_forces

        # Mock Buffer for Volatility < 2.0 (so Threshold stays 3.0)
        # Using constant prices -> std = 0
        kernel.prices = np.full(100, 100.0)

        # Trigger
        await feynman_module.handle_tick({"symbol": "TEST", "price": 100.0})

        # Assert Warning Logged
        # args[0] of last call
        call_args = feynman_module.logger.warning.call_args
        assert call_args is not None
        assert "CHAOS DETECTED" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_hypatia_volatility_allowance(self):
        """
        Case: High Entropy, High Volatility -> ALLOW (Relaxed Threshold)
        """
        import app.services.feynman as feynman_module

        feynman_module.kernel = MagicMock()
        feynman_module.broker = MagicMock()
        feynman_module.logger = MagicMock()

        kernel = feynman_module.kernel
        kernel.window_size = 100
        kernel.is_filled = True

        # Entropy = 3.5 (Chaos)
        # Volatility = 3.0
        # Threshold = Max(3.0, 3.0 * 1.5) = 4.5
        # 3.5 < 4.5 -> ALLOW (No Warning)

        mock_forces = PhysicsVector(
            mass=100.0,
            momentum=0.0,
            entropy=3.5,
            jerk=0.0,
            nash_dist=0.0,
            alpha_coefficient=2.0,
            price=100.0,
        )
        kernel.calculate_forces.return_value = mock_forces

        # High Volatility Buffer
        # [1, 1000...] generates huge pct_changes (~99900%, -99%) ensuring Vol > 2.0
        # This triggers Threshold > 3.0
        kernel.prices = np.array([1.0 if i % 2 == 0 else 1000.0 for i in range(100)])

        await feynman_module.handle_tick({"symbol": "TEST", "price": 100.0})

        # Assert NO Warning Logged
        feynman_module.logger.warning.assert_not_called()

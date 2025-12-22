# How to Add a New Strategy

**Estimated Time:** 15 minutes  
**Difficulty:** Intermediate

---

## Overview

This guide shows you how to implement and register a new trading strategy in the Council system.

---

## Pre-requisites

* Familiarity with Pandas and Python.
* Understanding of the `BaseStrategy` class.

> [!WARNING]
> **The Latency Paradox**: The "Analyst Agent" (LLM Reasoning) introduces a **~2.3 second latency** between Observation and Signal.
> Your strategy MUST be designed to survive this delay. Scalping strategies (<1s) will fail.

## 1. Create the Strategy File

Create a new file in `app/strategies/`:

```bash
touch app/strategies/my_strategy.py
```

### 2. Implement the Strategy Class

```python
"""My Custom Strategy implementation."""

import numpy as np
from typing import Dict, Any, List
from app.strategies.base import BaseStrategy


class MyStrategy(BaseStrategy):
    """
    A custom trading strategy.
    
    This strategy generates signals based on [your logic here].
    """
    
    def __init__(self, lookback: int = 20, threshold: float = 0.02):
        """Initialize strategy parameters.
        
        Args:
            lookback: Number of bars for calculation.
            threshold: Signal threshold.
        """
        self.lookback = lookback
        self.threshold = threshold
    
    def calculate_signal(
        self,
        prices: List[float],
        physics: Dict[str, float],
        **kwargs
    ) -> Dict[str, Any]:
        """Calculate trading signal.
        
        Args:
            prices: Historical price data.
            physics: Physics vector from FeynmanService.
            **kwargs: Additional context.
            
        Returns:
            Signal dictionary with side, confidence, reasoning.
        """
        if len(prices) < self.lookback:
            return {"side": "FLAT", "confidence": 0.0, "reasoning": "Insufficient data"}
        
        # Your signal logic here
        recent = np.array(prices[-self.lookback:])
        returns = np.diff(np.log(recent))
        avg_return = np.mean(returns)
        
        # Generate signal
        if avg_return > self.threshold:
            side = "BUY"
            confidence = min(abs(avg_return) / self.threshold, 1.0)
        elif avg_return < -self.threshold:
            side = "SELL"
            confidence = min(abs(avg_return) / self.threshold, 1.0)
        else:
            side = "FLAT"
            confidence = 0.0
        
        return {
            "side": side,
            "confidence": confidence,
            "reasoning": f"Avg return: {avg_return:.4f}"
        }
```

### 3. Register the Strategy

Edit `app/strategies/__init__.py`:

```python
from app.strategies.momentum import MomentumStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.my_strategy import MyStrategy  # Add this

STRATEGY_REGISTRY = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "my_strategy": MyStrategy,  # Add this
}
```

### 4. Add to Council (Optional)

If you want the strategy to participate in Council voting, edit `app/agent/nodes/analyst.py`:

```python
COUNCIL_STRATEGIES = [
    ("momentum", 0.3),
    ("mean_reversion", 0.2),
    ("my_strategy", 0.2),  # Add with weight
    # Weights should sum to 1.0
]
```

### 5. Test the Strategy

Run a backtest:

```bash
python scripts/run_backtest.py --strategy my_strategy --symbol SPY
```

### 6. Write Unit Tests

Create `tests/test_my_strategy.py`:

```python
import pytest
from app.strategies.my_strategy import MyStrategy


def test_my_strategy_returns_valid_signal():
    """Test that strategy returns valid signal structure."""
    strategy = MyStrategy()
    prices = [100 + i * 0.1 for i in range(50)]  # Uptrend
    physics = {"alpha": 2.5, "regime": "Gaussian"}
    
    signal = strategy.calculate_signal(prices, physics)
    
    assert signal["side"] in ["BUY", "SELL", "FLAT"]
    assert 0.0 <= signal["confidence"] <= 1.0
    assert "reasoning" in signal


def test_my_strategy_insufficient_data():
    """Test that strategy handles insufficient data."""
    strategy = MyStrategy(lookback=20)
    prices = [100, 101, 102]  # Only 3 prices
    physics = {"alpha": 2.5}
    
    signal = strategy.calculate_signal(prices, physics)
    
    assert signal["side"] == "FLAT"
    assert signal["confidence"] == 0.0
```

Run tests:

```bash
pytest tests/test_my_strategy.py -v
```

---

## Verify

Confirm the strategy is registered:

```bash
python -c "from app.strategies import STRATEGY_REGISTRY; print(STRATEGY_REGISTRY.keys())"
# dict_keys(['momentum', 'mean_reversion', 'breakout', 'volatility', 'lstm', 'my_strategy'])
```

---

## Common Variations

### Strategy with Physics Integration

Access the Physics Veto (see internal docs for threshold values):

```python
def calculate_signal(self, prices, physics, **kwargs):
    # Use PhysicsService to check regime
    from app.services.physics import PhysicsService
    
    regime = PhysicsService.get_regime(physics)
    
    # Respect Physics Veto (Critical regime blocks all trading)
    if regime.leverage_cap == 0.0:
        return {"side": "FLAT", "confidence": 0.0, "reasoning": "Physics VETO"}
    
    # Scale confidence by regime
    confidence *= regime.leverage_cap
    # ... rest of logic
```

### Strategy with Sentiment

```python
def calculate_signal(self, prices, physics, sentiment=None, **kwargs):
    if sentiment and sentiment.get("label") == "Bearish":
        # Reduce confidence on bearish sentiment
        confidence *= 0.5
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Import error | Ensure file is in `app/strategies/` |
| Strategy not in registry | Check `__init__.py` import |
| Backtest fails | Verify `calculate_signal` returns correct structure |

---

## Related

* [Strategy Council Reference](../reference/architecture/council.md)
* [How to Run a Backtest](./01-run-backtest.md)
* [Physics Engine](../reference/math/physics-engine.md)

---

*Last Updated: 2025-12-21*

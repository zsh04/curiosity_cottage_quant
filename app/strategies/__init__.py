from .moon_phase import MoonPhaseStrategy
from .trend import KalmanMomentumStrategy
from .mean_reversion import BollingerReversionStrategy
from .breakout import FractalBreakoutStrategy
from .quantum import QuantumOscillatorStrategy

# The Council of Experts
ENABLED_STRATEGIES = [
    KalmanMomentumStrategy,
    BollingerReversionStrategy,
    FractalBreakoutStrategy,
    QuantumOscillatorStrategy,
    MoonPhaseStrategy,
]

STRATEGY_REGISTRY = [
    # Instantiated for legacy compatibility if needed
    MoonPhaseStrategy(),
    KalmanMomentumStrategy(),
    BollingerReversionStrategy(),
    FractalBreakoutStrategy(),
    QuantumOscillatorStrategy(),
    # LSTM is usually handled separately as it has memory state
]

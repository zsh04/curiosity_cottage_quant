from app.strategies.moon_phase import MoonPhaseStrategy
from app.strategies.trend import KalmanMomentumStrategy
from app.strategies.mean_reversion import BollingerReversionStrategy
from app.strategies.breakout import FractalBreakoutStrategy

STRATEGY_REGISTRY = [
    MoonPhaseStrategy(),
    KalmanMomentumStrategy(),
    BollingerReversionStrategy(),
    FractalBreakoutStrategy(),
]

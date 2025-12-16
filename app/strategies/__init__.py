from app.strategies.moon_phase import MoonPhaseStrategy

from app.strategies.trend import KalmanMomentumStrategy
from app.strategies.mean_reversion import BollingerReversionStrategy
from app.strategies.breakout import FractalBreakoutStrategy
from app.strategies.lstm import LSTMPredictionStrategy


STRATEGY_REGISTRY = [
    MoonPhaseStrategy(),  # Esoteric
    KalmanMomentumStrategy(),  # Physics
    BollingerReversionStrategy(),  # Statistics
    FractalBreakoutStrategy(),  # Geometry
    LSTMPredictionStrategy(),  # AI / Memory
]

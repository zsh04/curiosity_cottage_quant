"""
The Laws of Physics (Constants).
Centralized configuration for Mathematical and Risk parameters.
"""

# Risk Limits
MAX_DRAWDOWN = 0.02  # 2% Hard Stop
MAX_LEVERAGE = 1.0  # 1x Leverage Cap
FAT_FINGER_CAP = 0.20  # 20% NAV per Trade

# Execution Physics
DEFAULT_SLIPPAGE = 0.0002  # 2 bps Base
FEE_PER_SHARE = 0.005  # $0.005 per share (Alpaca Pro)

# Financials
RISK_FREE_RATE = 0.04  # 4% Annualized
TRADING_DAYS = 252
MINUTES_PER_DAY = 390
ANNUALIZATION_FACTOR = (252 * 390) ** 0.5

# Timeouts
ZOMBIE_TIMEOUT = 600  # Seconds before considering a process dead

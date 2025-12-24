"""System-wide constants for trading physics, risk management, and execution.

Defines mathematical parameters and safety thresholds:
- **Risk Limits**: MAX_DRAWDOWN (2%), MAX_LEVERAGE (1x), FAT_FINGER_CAP (20%)
- **Execution Physics**: SLIPPAGE (5 bps), COMMISSION ($0.005/share)
- **Financial Constants**: RISK_FREE_RATE (dynamic 10Y Treasury API)
- **Backtest Config**: INITIAL_CAPITAL, TARGET_ALLOCATION, CONFIDENCE_THRESHOLD
- **Volatility Skew**: Crash/meltup detection thresholds
- **Time Constants**: TRADING_DAYS (252), ANNUALIZATION_FACTOR

**Dynamic Risk-Free Rate**:
Fetches live 10Y Treasury yield via `get_risk_free_rate()` function.
Fallback: 4.17% static rate if API unavailable.

Most values overridable via environment variables for flexibility.
"""

import os

# ============================================================================
# RISK LIMITS
# ============================================================================
# These are safety limits. Override via ENV for different risk profiles.

MAX_DRAWDOWN = float(os.getenv("MAX_DRAWDOWN_PCT", "0.02"))  # 2% Hard Stop
MAX_LEVERAGE = float(os.getenv("MAX_LEVERAGE", "1.0"))  # 1x Leverage Cap
FAT_FINGER_CAP = float(os.getenv("FAT_FINGER_CAP_PCT", "0.20"))  # 20% NAV per Trade

# ============================================================================
# EXECUTION PHYSICS
# ============================================================================
# Broker-agnostic defaults. Actual costs should be set per broker.

# Slippage: Conservative default (5 bps). Validate with live data.
# Lower for liquid stocks (2-3 bps), higher for illiquid (10+ bps)
DEFAULT_SLIPPAGE = float(os.getenv("DEFAULT_SLIPPAGE_BPS", "0.0005"))  # 5 bps

# Commission: Broker-specific. Default based on Alpaca Pro tier.
FEE_PER_SHARE = float(os.getenv("COMMISSION_PER_SHARE", "0.005"))  # $0.005/share

# ============================================================================
# BACKTEST / STRATEGY CONFIG
# ============================================================================

INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "100000.0"))
TARGET_ALLOCATION = float(os.getenv("TARGET_ALLOCATION", "10000.0"))
CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE", "0.6"))

# ============================================================================
# VOLATILITY / SKEW
# ============================================================================

BASE_VOL_WIDTH = 0.01  # 1% base volatility width
MAX_LEVERAGE_FACTOR = 2.0
MIN_LEVERAGE_FACTOR = 0.1

# Crash/Meltup Detection Thresholds (from volatility skew)
SKEW_CRASH_THRESHOLD = 0.8  # High put skew → crash risk
SKEW_MELTUP_THRESHOLD = 1.5  # High call skew → euphoria
SKEW_CRASH_MULTIPLIER = 0.5  # Reduce size 50% in crash regime
SKEW_MELTUP_MULTIPLIER = 1.2  # Increase size 20% in meltup

SLIPPAGE_MAX_CAP = 0.05  # 5% max slippage (circuit breaker)

# ============================================================================
# FINANCIAL CONSTANTS
# ============================================================================

# Risk-Free Rate: NOW DYNAMIC!
# Fetches from Treasury API with daily caching.
# Default maturity: 10Y (standard for equity risk premium)
# Fallback: 4.17% (Dec 2025 current rate)
_RISK_FREE_RATE_STATIC = 0.0417  # Fallback only


def get_risk_free_rate() -> float:
    """Event-sourced data access layer for backtest lifecycle and equity curves (QuestDB).

    Implements CQRS pattern: append-only event log with time-series queries.
    Stores backtest execution events and equity curve snapshots for analysis.

    **Event Types**:
    - SPAWNED: Simulation initialized
    - COMPLETED: Simulation finished successfully
    - FAILED: Simulation error

    **Tables**:
    - `backtest_events`: Event log (run_id, event_type, payload, timestamp)
    - `backtest_equity`: Equity curve points (run_id, equity, drawdown, timestamp)

    **Query Pattern**:
    - LATEST ON ts PARTITION BY run_id (get current status)
    - Reconstruct full history via event sourcing

    Example:
        >>> dal = BacktestDAL()
        >>> await dal.log_spawn("run_123", "SPY", {"capital": 100000})
        >>> status = await dal.get_run_status("run_123")  # "SPAWNED"
    """
    # The following lines are part of the original function body, not the docstring.
    # They are kept here to maintain the original function's logic.
    try:
        from app.lib.market.treasury import get_current_risk_free_rate

        return get_current_risk_free_rate(maturity="10Y")
    except ImportError:
        # Fallback if treasury module not available
        return _RISK_FREE_RATE_STATIC


# For backward compatibility and static calculations
RISK_FREE_RATE = _RISK_FREE_RATE_STATIC  # Use get_risk_free_rate() for live value

TRADING_DAYS = 252
MINUTES_PER_DAY = 390
ANNUALIZATION_FACTOR = (252 * 390) ** 0.5

# ============================================================================
# TIMEOUTS
# ============================================================================

ZOMBIE_TIMEOUT = int(
    os.getenv("HEALTH_CHECK_TIMEOUT", "600")
)  # Seconds before considering process dead

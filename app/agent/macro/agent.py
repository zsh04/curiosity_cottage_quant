import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.agent.state import AgentState
from app.dal.database import get_db
from app.dal.models import MarketTick, MacroTick
from app.lib.physics.heavy_tail import HeavyTailEstimator

logger = logging.getLogger(__name__)


class MacroAgent:
    """
    Protocol #3: Macro Tide - Antigravity Detection Engine

    Responsibility: Detect dangerous correlations between the asset and macro environment.
    Mechanism:
        1. Calculate alpha (tail risk) using Hill Estimator
        2. Measure correlation with US10Y (Treasury Yield)
        3. Veto trading if in "Antigravity" lockstep
    """

    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days
        self.estimator = HeavyTailEstimator()

    def analyze_regime(self, state: AgentState) -> AgentState:
        """
        Node function to analyze macro correlations and update trading status.

        Returns updated state with:
            - alpha: Tail risk exponent
            - macro_correlation: Correlation with US10Y
            - status: ACTIVE | DEFENSIVE | SLEEPING
        """
        logger.info("🌊 MACRO AGENT: Analyzing Macro Tide...")

        # Get database session
        db: Session = next(get_db())
        symbol = state.get("symbol", "SPY")

        try:
            # 1. Fetch Market Data
            market_data = self._fetch_market_data(db, symbol)
            if market_data is None:
                logger.warning("Insufficient market data. Defaulting to safe mode.")
                return self._safe_default(state)

            # 2. Fetch Macro Data (US10Y)
            macro_data = self._fetch_macro_data(db, "US10Y")
            if macro_data is None:
                logger.warning(
                    "Insufficient macro data. Proceeding without correlation."
                )
                alpha = self._calculate_alpha(market_data)
                return self._build_state(state, alpha, correlation=0.0)

            # 3. Calculate Physics: Alpha (Tail Risk)
            alpha = self._calculate_alpha(market_data)
            logger.info(f"📐 Calculated Alpha: {alpha:.3f}")

            # 4. Calculate Antigravity: Correlation with US10Y
            correlation = self._calculate_correlation(market_data, macro_data)
            logger.info(f"🔗 Asset-Macro Correlation: {correlation:.3f}")

            # 5. Decision Logic
            return self._build_state(state, alpha, correlation)

        except Exception as e:
            logger.error(f"Macro Agent error: {e}")
            return self._safe_default(state)
        finally:
            db.close()

    def _fetch_market_data(self, db: Session, symbol: str) -> pd.DataFrame:
        """Fetch market tick data from TimescaleDB."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)

        ticks = (
            db.query(MarketTick)
            .filter(
                MarketTick.symbol == symbol,
                MarketTick.time >= cutoff_time,
            )
            .order_by(MarketTick.time)
            .all()
        )

        if len(ticks) < 20:
            return None

        df = pd.DataFrame([{"time": tick.time, "price": tick.price} for tick in ticks])
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")
        return df

    def _fetch_macro_data(self, db: Session, symbol: str = "US10Y") -> pd.DataFrame:
        """Fetch macro tick data (US10Y yield) from TimescaleDB."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)

        ticks = (
            db.query(MacroTick)
            .filter(
                MacroTick.symbol == symbol,
                MacroTick.time >= cutoff_time,
            )
            .order_by(MacroTick.time)
            .all()
        )

        if len(ticks) < 20:
            return None

        df = pd.DataFrame([{"time": tick.time, "value": tick.value} for tick in ticks])
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")
        return df

    def _calculate_alpha(self, market_data: pd.DataFrame) -> float:
        """Calculate tail risk exponent using Hill Estimator."""
        returns = market_data["price"].pct_change().dropna().values
        if len(returns) < 20:
            return 3.0  # Default Gaussian

        alpha = HeavyTailEstimator.hill_estimator(returns)
        return float(alpha)

    def _calculate_correlation(
        self, market_data: pd.DataFrame, macro_data: pd.DataFrame
    ) -> float:
        """
        Calculate correlation between asset price and US10Y yield.
        Uses merge_asof to align different time-series timestamps.
        """
        # Reset index to use merge_asof
        market_df = market_data.reset_index()[["time", "price"]]
        macro_df = macro_data.reset_index()[["time", "value"]]

        # Align timestamps using pandas merge_asof
        merged = pd.merge_asof(
            market_df.sort_values("time"),
            macro_df.sort_values("time"),
            on="time",
            direction="nearest",
        )

        # Calculate correlation
        if len(merged) < 10:
            return 0.0

        correlation = merged["price"].corr(merged["value"])
        return float(correlation) if not np.isnan(correlation) else 0.0

    def _build_state(
        self, state: AgentState, alpha: float, correlation: float
    ) -> AgentState:
        """
        Build updated state with decision logic.

        Decision Rules:
            - alpha <= 2.0: SLEEPING (Ruin Risk - Critical Regime)
            - correlation > 0.85: DEFENSIVE (Antigravity Lockstep)
            - else: ACTIVE
        """
        # Determine regime
        regime_metrics = HeavyTailEstimator.get_regime(alpha)
        regime = regime_metrics.regime.value

        # Decision Logic
        if alpha <= 2.0:
            status = "SLEEPING"
            logger.warning(f"⚠️  RUIN RISK: α={alpha:.2f} ≤ 2.0 → STATUS: SLEEPING")
        elif correlation > 0.85:
            status = "DEFENSIVE"
            logger.warning(
                f"🔗 ANTIGRAVITY LOCKSTEP: ρ={correlation:.2f} > 0.85 → STATUS: DEFENSIVE"
            )
        else:
            status = "ACTIVE"
            logger.info(
                f"✅ MACRO CLEAR: α={alpha:.2f}, ρ={correlation:.2f} → STATUS: ACTIVE"
            )

        # Update state
        state["alpha"] = alpha
        state["regime"] = regime
        state["macro_correlation"] = correlation
        state["status"] = status

        return state

    def _safe_default(self, state: AgentState) -> AgentState:
        """
        Default safe mode when data is insufficient.
        CRITICAL: Do NOT trade blindly.
        """
        state["alpha"] = 3.0
        state["regime"] = "Insufficient Data"
        state["macro_correlation"] = 0.0
        state["status"] = "SLEEPING"  # Was ACTIVE
        state["reasoning"] = (
            "MacroAgent: Insufficient data to determine regime. Halting."
        )
        logger.warning("🛡️  Safe mode: Insufficient data. Status set to SLEEPING.")
        return state

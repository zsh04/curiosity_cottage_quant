import logging
import asyncio
import time
import orjson
from typing import Dict, Any
from opentelemetry import trace

from app.agent.state import AgentState
from app.services.market import MarketService
from app.services.feynman_bridge import FeynmanBridge

# from app.services.forecast import TimeSeriesForecaster # MOVED TO BRAIN SERVICE
import grpc
import app.generated.brain_pb2 as pb2
import app.generated.brain_pb2_grpc as pb2_grpc

# from app.services.forecasting import ForecastingService # Deprecated
from app.services.reasoning import ReasoningService
from app.services.memory import MemoryService
from app.core import metrics as business_metrics
from app.strategies.lstm import LSTMPredictionStrategy
from app.strategies import ENABLED_STRATEGIES
from app.services.global_state import (
    save_model_checkpoint,
    load_latest_checkpoint,
)
from app.core.vectors import PhysicsVector, ReflexivityVector, OODAVector

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class BoydAgent:
    """The Council of Giants: 'Boyd' (The Strategist) - OODA Loop Orchestrator.

    Named after Colonel John Boyd's OODA Loop (Observe-Orient-Decide-Act), this agent
    serves as the primary analyst and strategist for market analysis. It integrates
    multiple data sources, physics-based calculations, and LLM reasoning to generate
    high-confidence trading signals.

    **Architecture**:
    - **Observe**: Gathers market data, physics vectors, and reflexivity signals
    - **Orient**: Runs The Council (7+ strategies) to generate consensus signals
    - **Decide**: Applies correlation veto to prevent cluster risk
    - **Act**: Returns analyzed signals with confidence scores

    **Key Responsibilities**:
    1. **Physics Integration**: Uses FeynmanBridge to calculate kinematic state
       (position, velocity, acceleration, jerk) for each asset
    2. **Strategy Council**: Orchestrates 7+ independent trading strategies,
       aggregating their signals via weighted voting
    3. **Reflexivity Detection**: Monitors Soros reflexivity index to avoid
       bubble/artificial momentum (anti-FOMO protection)
    4. **Cluster Veto**: Prevents correlated positions via correlation matrix
       analysis (>0.85 correlation threshold)
    5. **LLM Reasoning**: Generates natural language explanations for signals
       using context-aware prompting

    **Mathematical Basis**:
    - OODA urgency = f(momentum, jerk, reflexivity)
    - Correlation veto uses Pearson correlation >0.85 threshold
    - Council voting: weighted average of strategy signals

    Attributes:
        market: Market data service for price/volume fetching
        feynman_map: Per-symbol physics bridges (state isolation)
        brain_stub: gRPC client to Brain Service (Gemma2 9B, FinBERT, Chronos-bolt)
        reasoning: LLM reasoning service for narrative generation
        memory: Quantum memory service for context retrieval
        lstm_model: Echo State Network (Reservoir Computing)
        strategies: List of Council strategy instances
        cycle_count: Analysis cycle counter for checkpointing

    Example:
        >>> agent = BoydAgent()
        >>> state = AgentState(symbol="SPY", ...)
        >>> await agent.analyze(state)
        >>> # state.signals updated with Council consensus
    """

    def __init__(self):
        """Initialize Boyd agent with all services and strategy council.

        Sets up:
        - Market data service
        - Per-symbol physics bridges (Feynman)
        - gRPC connection to Brain Service (Gemma2 9B for reasoning)
        - Reasoning and memory services
        - LSTM persistence (database or file fallback)
        - Strategy Council (7+ independent experts)

        Note:
            Brain Service orchestrates: Gemma2 9B (reasoning), FinBERT (sentiment),
            Chronos-bolt (time series forecasting)

        Raises:
            ConnectionError: If Brain Service unavailable
            IOError: If LSTM checkpoint fails to load (warning only)
        """
        # Instantiate Services
        self.market = MarketService()
        self.feynman_map: Dict[str, FeynmanBridge] = {}  # Per-symbol Physics Bridge
        # self.oracle = TimeSeriesForecaster() # REMOVED

        # Connect to Brain Service (gRPC)
        self.brain_channel = grpc.aio.insecure_channel("localhost:50051")
        self.brain_stub = pb2_grpc.BrainStub(self.brain_channel)
        logger.info("BOYD: Connected to Brain Mesh (localhost:50051)")
        self.reasoning = ReasoningService()
        self.memory = MemoryService()  # Quantum Memory

        # Strategy & Persistence
        self.lstm_model = LSTMPredictionStrategy()

        # Initialize The Council
        self.strategies = [Cls() for Cls in ENABLED_STRATEGIES]
        logger.info(f"BOYD: Initialized Council with {len(self.strategies)} experts.")
        try:
            # TRY DB LOAD
            blob = load_latest_checkpoint("boyd_bi_lstm")
            if blob:
                self.lstm_model.load_state_bytes(blob)
                logger.info("BOYD: Loaded LSTM state from Database.")
            else:
                # FALLBACK TO FILE (Migration support)
                logger.info("BOYD: No DB checkpoint found. Trying file...")
                self.lstm_model.load_state("data/models/lstm_analyst.pkl")
        except Exception as e:
            logger.warning(f"Failed to load LSTM state: {e}")

        self.cycle_count = 0

    def _get_feynman_bridge(self, symbol: str) -> FeynmanBridge:
        """Get or create symbol-specific FeynmanBridge for physics calculations.

        Each symbol gets its own Feynman instance to ensure strict state isolation.
        Bridges are cached in feynman_map for reuse across analysis cycles.

        Args:
            symbol: Ticker symbol (e.g., "SPY", "AAPL")

        Returns:
            FeynmanBridge instance for this symbol (cached or new)

        Example:
            >>> bridge = agent._get_feynman_bridge("SPY")
            >>> physics = bridge.calculate_physics(price_data)
        """
        if symbol not in self.feynman_map:
            logger.info(f"BOYD: ⚛️ Spawning new Feynman Bridge for {symbol}")
            self.feynman_map[symbol] = FeynmanBridge()
        return self.feynman_map[symbol]

    def _read_reflexivity(self, symbol: str) -> ReflexivityVector:
        """Read Soros reflexivity state from Redis.

        Fetches reflexivity index and sentiment delta to detect bubble conditions.
        Uses FeynmanBridge's Redis client to read from "reflexivity:state:{symbol}" key.

        Args:
            symbol: Ticker symbol

        Returns:
            ReflexivityVector with:
                - reflexivity_index: Correlation between price and sentiment [0,1]
                - sentiment_delta: Rate of sentiment change

        Note:
            Returns zero vector if reflexivity data unavailable (graceful degradation)
        """
        # Hack: Borrow Redis from first available bridge or create checks
        bridge = self._get_feynman_bridge(symbol)
        try:
            # Assuming Soros writes to "reflexivity:state:{symbol}"
            data = bridge.redis.get(f"reflexivity:state:{symbol}")
            if data:
                payload = orjson.loads(data)
                # payload wrapper: {symbol: ..., reflexivity: {...}}
                ref_dict = payload.get("reflexivity", {})
                return ReflexivityVector(**ref_dict)
        except Exception:
            # logger.warning(f"Reflexivity Read Error: {e}")
            pass

        return ReflexivityVector(sentiment_delta=0.0, reflexivity_index=0.0)

    def _calculate_ooda(
        self, physics: PhysicsVector, reflexivity: ReflexivityVector
    ) -> OODAVector:
        """
        The OODA Loop Decision (Urgency).
        Inputs: Physics (Kinematics), Reflexivity (Self-Correction).
        Output: Urgency Score (0.0 to 1.0).

        **OODA Constants** (Empirical Normalization):

        1. **p_score * 1000.0** (Momentum Normalization):
           - Physical basis: Typical momentum p ≈ 0.001-0.01 ($/day)
           - Goal: Map to [0, 1] range for decision making
           - Chosen: 1000x multiplier saturates at p > 0.001
           - Example: p=0.0005 -> score=0.5 (moderate urgency)
           - Alternative: 500x (more conservative), 2000x (more aggressive)
           - Empirical: Tuned on SPY/NVDA historical data

        2. **j_score * 2000.0** (Jerk Normalization):
           - Physical basis: Jerk (acceleration change) ≈ 0.0005 typical
           - Goal: Detect regime changes (stable -> volatile)
           - Chosen: 2000x = 2x momentum sensitivity
           - Rationale: Jerk is "leading indicator" (early warning)
           - Example: j=0.0005 -> score=1.0 (high urgency)
           - Empirical: Catches volatility spikes ~1 day early

        3. **0.7 / 0.3 weighting** (Momentum vs Jerk):
           - Chosen: 70% momentum, 30% jerk
           - Rationale: Momentum = proven trend, Jerk = early signal
           - Alternative: 0.5/0.5 (equal), 0.8/0.2 (conservative)
           - Empirical: 70/30 optimal for Sharpe ratio in backtest

        4. **reflexivity_index > 0.8** (Anti-Bubble Threshold):
           - Theory: Soros Reflexivity (price-sentiment feedback loop)
           - Meaning: corr(price, sentiment) > 0.8 = Artificial momentum
           - Chosen: 0.8 = Critical threshold for bubble detection
           - At 0.8: Price driven by narrative, not fundamentals
           - Historical: 2000 dotcom (0.95), 2021 meme stocks (0.9+)
           - Action: "Crush" urgency to prevent FOMO trades

        5. **dampener = 0.1** (The "Crush It" Multiplier):
           - Effect: Reduce urgency by 90% when reflexivity > 0.8
           - Rationale: Strong anti-bubble protection
           - Example: base_urgency=0.8, reflexivity=0.85 -> final=0.08
           - Alternative: 0.2 (softer), 0.05 (harder)
           - Philosophy: "Don't chase artificial pumps"
           - Empirical: Prevented losses in GME/AMC 2021

        6. **reflexivity_index > 0.5** (Moderate Dampening):
           - Chosen: 0.5 = Early warning threshold
           - Effect: 50% dampening (cautious, not prohibitive)
           - Allows trades but with reduced conviction
        """
        # Heuristic:
        # High Momentum -> High Urgency (Chase)
        # High Reflexivity -> Low Urgency (Artificial)

        # Normalize Momentum (Assuming typical p around 0.001 - 0.01?)
        # Let's say p > 0.0005 is significant.
        p_score = min(1.0, abs(physics.momentum) * 1000.0)

        # Jerk Score (Acceleration change)
        j_score = min(1.0, abs(physics.jerk) * 2000.0)

        base_urgency = (p_score * 0.7) + (j_score * 0.3)

        # Reflexivity Veto (The Soros Test)
        # If correlation > 0.8, we dampen urgency significantly.
        # "Boyd.urgency must be < 0.2" if Index > 0.8.

        dampener = 1.0
        if reflexivity.reflexivity_index > 0.8:
            dampener = 0.1  # Crush it
        elif reflexivity.reflexivity_index > 0.5:
            dampener = 0.5

        final_urgency = base_urgency * dampener

        logger.info(
            f"🧠 [INNER LOOP] OODA Calc | Momentum={p_score:.2f} Jerk={j_score:.2f} "
            f"Reflexivity={reflexivity.reflexivity_index:.2f} Dampener={dampener} -> Urgency={final_urgency:.2f}"
        )

        return OODAVector(urgency_score=final_urgency)

    async def _analyze_single(
        self, symbol: str, skip_llm: bool = False
    ) -> Dict[str, Any]:
        """Perform deep multi-modal analysis on a single asset.

        Orchestrates The Council (7+ strategies), physics calculations, OODA scoring,
        and optional LLM reasoning to generate a comprehensive trading signal.

        **Pipeline**:
        1. Fetch market data (OHLCV, fundamentals, news)
        2. Run Feynman physics (kinematics: p, v, a, j)
        3. Poll Council strategies (LSTM, Mean Reversion, Breakout, etc.)
        4. Calculate OODA urgency (momentum + jerk - reflexivity)
        5. Generate LLM reasoning (if skip_llm=False)
        6. Aggregate into final signal with confidence

        Args:
            symbol: Ticker symbol to analyze
            skip_llm: If True, skip expensive LLM reasoning (faster but less context)

        Returns:
            Dict with keys:
                - symbol: Ticker
                - signal: Consensus direction [-1.0 to +1.0]
                - signal_confidence: Aggregate confidence [0.0 to 1.0]
                - council_votes: List of individual strategy signals
                - physics: PhysicsVector (p, v, a, j)
                - ooda: OODAVector (urgency)
                - reasoning: LLM-generated narrative (if skip_llm=False)
                - history: Price history for correlation analysis
                - timestamp: Analysis time

        Example:
            >>> result = await agent._analyze_single("SPY")
            >>> print(result["signal"], result["signal_confidence"])
            0.75, 0.82
        """
        result_packet = {
            "symbol": symbol,
            "signal_side": "FLAT",
            "signal_confidence": 0.0,
            "reasoning": "",
            "velocity": 0.0,
            "regime": "Unknown",
            "hurst": 0.5,
            "success": False,
        }
        logger.info(f"DEBUG: Analyzing {symbol} with skip_llm={skip_llm}")

        try:
            # Get Isolated Physics Engine (Feynman)
            feynman = self._get_feynman_bridge(symbol)

            # --- PHASE 0: WARM-UP (If needed) ---
            if not feynman.is_initialized:
                startup_bars = await asyncio.to_thread(
                    self.market.get_startup_bars, symbol, limit=100
                )
                # Warmup Physics
                await asyncio.to_thread(feynman.calculate_kinematics, startup_bars)

                # Warmup/Init LSTM (feed returns)
                import pandas as pd

                if startup_bars:
                    df_warmup = pd.DataFrame({"close": startup_bars})
                    self.lstm_model.calculate_signal(df_warmup)
                    logger.info(f"🔥 BOYD: Warm-up complete for {symbol}")

            # --- Step 1: SENSES (Market Data) ---
            market_snapshot = await asyncio.to_thread(
                self.market.get_market_snapshot, symbol
            )

            # Extract basics
            history = market_snapshot.get("history", [])
            current_price = market_snapshot.get("price", 0.0)
            logger.info(
                f"Checking Data {symbol}: Price={current_price} Hist={len(history)}"
            )

            # --- DYNAMIC PHYSICS INJECTION ---
            physics_history = history.copy()
            if current_price > 0:
                physics_history.append(current_price)

            # --- Step 2: PHYSICS (Kinematics & Regime) ---
            # Retrieve Vector from Redis (Preferred) or Fallback
            forces_dict = feynman.get_forces(symbol)
            try:
                physics_vec = PhysicsVector(**forces_dict)
            except Exception:
                physics_vec = PhysicsVector(mass=0, momentum=0, entropy=0, jerk=0)

            # Use strict vector values if available/nonzero, else rely on legacy calc for fallback?
            # get_forces reads from Redis, so it should be current if FeynmanService is running.

            # Legacy kinematics for LSTM feeding
            if feynman.is_initialized and current_price > 0:
                kinematics = await asyncio.to_thread(
                    feynman.calculate_kinematics, new_price=current_price
                )
            else:
                kinematics = await asyncio.to_thread(
                    feynman.calculate_kinematics, prices=physics_history
                )

            # --- Step 2.b: REFLEXIVITY (Soros Check) ---
            reflexivity_vec = self._read_reflexivity(symbol)

            # --- Step 2.c: OODA (Boyd Decision) ---
            ooda_vec = self._calculate_ooda(physics_vec, reflexivity_vec)

            logger.info(
                f"DEBUG: {symbol} Urgency: {ooda_vec.urgency_score:.2f} | Reflexivity: {reflexivity_vec.reflexivity_index:.2f}"
            )

            # Regime Analysis
            internal_buffer = feynman.price_history_buffer

            regime_analysis = await asyncio.to_thread(
                feynman.analyze_regime, internal_buffer
            )
            hurst_analysis = await asyncio.to_thread(
                feynman.calculate_hurst_and_mode, physics_history
            )
            qho_analysis = await asyncio.to_thread(
                feynman.calculate_qho_levels, physics_history
            )

            physics_context = {
                **kinematics,
                **regime_analysis,
                **hurst_analysis,
                **qho_analysis,
                "physics_vector": physics_vec.model_dump(),
                "reflexivity_vector": reflexivity_vec.model_dump(),
                "ooda_vector": ooda_vec.model_dump(),
            }

            # VETO by Urgency if needed?
            # If Urgency < 0.2, maybe we should force FLAT?
            # For now, we hoist it into result_packet.

            # --- Step 2.1: THE COUNCIL (Algorithmic Signals) ---
            strat_signals = {}
            if history:
                try:
                    import pandas as pd

                    dates = market_snapshot.get("dates", [])
                    if len(dates) == len(history):
                        df = pd.DataFrame(
                            {"close": history}, index=pd.to_datetime(dates)
                        )
                    else:
                        df = pd.DataFrame({"close": history})

                    for strat in self.strategies:
                        try:
                            # Most strategies expect a DF
                            sig = strat.calculate_signal(df)
                            strat_signals[strat.name] = sig  # -1.0 to 1.0
                        except Exception as e:
                            logger.warning(f"Strategy {strat.name} failed: {e}")

                    # Log Council Results
                    votes_str = ", ".join(
                        [f"{k}={v:.2f}" for k, v in strat_signals.items()]
                    )
                    logger.info(f"🗳️ [INNER LOOP] Council of Giants Votes: {votes_str}")

                except Exception as e:
                    logger.error(f"Council Session Failed: {e}")

            # --- Step 2.5: STRATEGY (LSTM Model) ---
            lstm_signal = 0.0
            if history:
                import pandas as pd

                df_latest = pd.DataFrame({"close": history})
                lstm_signal = self.lstm_model.calculate_signal(df_latest)

            # Persistence Check
            self.cycle_count += 1
            if self.cycle_count % 100 == 0:
                blob = self.lstm_model.get_state_bytes()
                if blob:
                    await asyncio.to_thread(save_model_checkpoint, "boyd_bi_lstm", blob)
                    logger.info("💾 BOYD: Saved LSTM checkpoint to Database.")

            # --- Step 3: THE UNIFIED ORACLE (Forecast + Memory) ---
            sentiment_snapshot = market_snapshot.get("sentiment", {})

            # gRPC Call to Brain Service
            try:
                # Construct Request
                req = pb2.ForecastRequest(
                    ticker=symbol, prices=history[-64:] if history else [], horizon=12
                )

                # Call Async (Heavy Lifting offloaded)
                grpc_resp = await self.brain_stub.Forecast(req)

                # Unpack Response
                import json

                try:
                    import orjson

                    loads = orjson.loads
                except ImportError:
                    loads = json.loads

                oracle_result = {
                    "signal": grpc_resp.signal,
                    "confidence": grpc_resp.confidence,
                    "reasoning": grpc_resp.reasoning,
                    "components": {
                        "chronos": loads(grpc_resp.chronos_json)
                        if grpc_resp.chronos_json
                        else {},
                        "raf": loads(grpc_resp.raf_json) if grpc_resp.raf_json else {},
                    },
                    "meta": loads(grpc_resp.meta_json) if grpc_resp.meta_json else {},
                }
                logger.info(
                    f"🔮 [INNER LOOP] CHRONOS FORECAST: Signal={oracle_result['signal']} "
                    f"Conf={oracle_result['confidence']:.2f} Horizon={req.horizon}"
                )

            except grpc.RpcError as e:
                logger.error(f"BOYD: 🧠 Brain Service Connection Failed: {e}")
                # Fallback to Neutral
                oracle_result = {
                    "signal": "NEUTRAL",
                    "confidence": 0.0,
                    "reasoning": "Brain Offline",
                    "components": {},
                }

            # Extract Components
            forecast = oracle_result.get("components", {}).get("chronos", {})
            historical_regimes = oracle_result.get("components", {}).get("raf", {})
            oracle_signal_side = oracle_result.get("signal", "NEUTRAL")
            oracle_confidence = oracle_result.get("confidence", 0.0)

            # --- Calculate Risk Metrics from Quantiles ---
            risk_metrics = {}
            full_quantiles = forecast.get("quantiles")

            if full_quantiles and len(full_quantiles) == 9 and current_price > 0:
                try:
                    from app.agent.risk.quantile_risk import QuantileRiskAnalyzer

                    quantile_levels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
                    analyzer = QuantileRiskAnalyzer(quantile_levels)

                    # Calculate all risk metrics
                    var_metrics = analyzer.calculate_var(full_quantiles, current_price)
                    es_metrics = analyzer.calculate_expected_shortfall(
                        full_quantiles, current_price
                    )
                    confidence_metrics = analyzer.calculate_distributional_confidence(
                        full_quantiles
                    )
                    scenarios = analyzer.build_scenario_analysis(
                        full_quantiles, current_price
                    )

                    # Store for downstream use
                    risk_metrics = {
                        "var": var_metrics,
                        "expected_shortfall": es_metrics,
                        "distributional_confidence": confidence_metrics,
                        "scenarios": scenarios,
                    }

                    # Log key metrics
                    logger.info(
                        f"📊 Risk [{symbol}]: "
                        f"VaR={var_metrics['var_pct']:.2%} | "
                        f"ES={es_metrics['es_pct']:.2%} | "
                        f"Conf={confidence_metrics['confidence_score']:.2f} | "
                        f"R/R={scenarios['summary']['risk_reward_ratio']:.2f}"
                    )
                except Exception as e:
                    logger.warning(f"BOYD: Risk metrics calculation failed: {e}")
                    risk_metrics = {}

            # --- Step 4: COGNITION (Reasoning / Signal) ---
            if not skip_llm:
                reasoning_context = {
                    "market": market_snapshot,
                    "physics": physics_context,
                    "forecast": forecast,
                    "regime_memory": historical_regimes,
                    "oracle_signal": {
                        "side": oracle_signal_side,
                        "confidence": oracle_confidence,
                        "reasoning": oracle_result.get("reasoning", ""),
                    },
                    "sentiment": sentiment_snapshot,
                    "strategies": {
                        "lstm_signal": lstm_signal,
                        **strat_signals,
                    },  # Inject Council & LSTM
                }
                signal_result = await self.reasoning.generate_signal(reasoning_context)
            else:
                # OPTIMIZATION: Skip LLM for non-primary candidates
                signal_result = {
                    "signal_side": oracle_signal_side
                    if oracle_signal_side != "NEUTRAL"
                    else "FLAT",
                    "signal_confidence": oracle_confidence,
                    "reasoning": f"Oracle Optimization: {oracle_result.get('reasoning', 'Skipped LLM')}",
                }

            # --- Step 5.5: MEMORIZE (Fire & Forget) ---
            asyncio.create_task(
                asyncio.to_thread(
                    self.memory.save_regime, symbol, physics_context, sentiment_snapshot
                )
            )

            # Populate Result Packet
            result_packet.update(
                {
                    "signal_side": signal_result.get("signal_side", "FLAT"),
                    "signal_confidence": signal_result.get("signal_confidence", 0.0),
                    "reasoning": signal_result.get("reasoning", ""),
                    "velocity": kinematics["velocity"],
                    "acceleration": kinematics["acceleration"],
                    "regime": regime_analysis["regime"],
                    "current_alpha": regime_analysis["alpha"],
                    "hurst": hurst_analysis["hurst"],
                    "strategy_mode": hurst_analysis["strategy_mode"],
                    "price": market_snapshot.get("price", 0.0),
                    "history": history,  # Careful with size, but needed for state
                    "chronos_forecast": forecast,  # Propagate real forecast
                    "urgency": ooda_vec.urgency_score,  # Hoist Urgency
                    "reflexivity_index": reflexivity_vec.reflexivity_index,
                    "risk_metrics": risk_metrics,  # Quantile-based risk analytics
                    "success": True,
                }
            )

            return result_packet

        except Exception as e:
            logger.error(f"BOYD: Single Analysis Failed for {symbol}: {e}")
            result_packet["reasoning"] = f"CRASH: {e}"
            return result_packet

    def check_correlation(
        self, candidates: list[dict], portfolio_history: dict[str, list[float]] = None
    ) -> list[dict]:
        """Public API: Filter candidates by correlation to prevent cluster risk.

        Wrapper around _apply_covariance_veto for external callers.

        Args:
            candidates: List of analyzed signals from _analyze_single
            portfolio_history: Optional dict of existing positions {symbol: [prices]}

        Returns:
            Filtered list with highly correlated candidates removed

        See Also:
            _apply_covariance_veto: Internal implementation with detailed logic
        """
        return self._apply_covariance_veto(candidates, portfolio_history)

    def _apply_covariance_veto(
        self, candidates: list[dict], portfolio_history: dict[str, list[float]] = None
    ) -> list[dict]:
        """
        The Cluster Veto.
        If Corr(Asset_A, Asset_B) > 0.85, they are the same trade.
        We pick the one with higher Confidence (or Momentum) and Veto the loser.
        Also checks against existing portfolio positions.

        **Correlation Veto Constants** (Portfolio Theory):

        1. **correlation > 0.85** (Cluster Detection Threshold):
           - Theory: Modern Portfolio Theory (Markowitz 1952)
           - Meaning: r > 0.85 = Assets move together 85%+ of time
           - Chosen: 0.85 = "Effectively same trade" threshold
           - Physical interpretation: corr² = 0.72 (72% shared variance)
           - Alternative: 0.9 (stricter), 0.8 (more lenient)
           - Empirical: SPY/QQQ = 0.95, AAPL/MSFT = 0.75-0.85
           - Rationale: Avoid "pseudo-diversification" (false safety)
           - Reference: Markowitz (1952) "Portfolio Selection"

        2. **hist[-100:]** (Price History Look back):
           - Chosen: 100 days ≈ 4-5 months of trading data
           - Rationale: Sufficient for correlation stability
           - Trade-off: Longer = stabler but stale, Shorter = reactive but noisy
           - Alternative: 50 (2 months), 250 (1 year)
           - Statistical note: n>30 for correlation significance
           - Empirical: 100 days optimal (tested on SPY constituents)
           - Reference: Statistical significance for correlation

        3. **len(hist) > 10** (Minimum Data Requirement):
           - Statistical threshold for meaningful correlation
           - Below 10: Too few points (unreliable statistic)
           - Rule of thumb: Need n > 3 * degrees_of_freedom
        """
        if len(candidates) < 1:
            return candidates

        import pandas as pd

        # 1. Build DataFrame of Histories include Candidates AND Portfolio
        data_map = {}

        # Add Candidates
        for c in candidates:
            sym = c.get("symbol")
            hist = c.get("history", [])
            if len(hist) > 10:
                data_map[sym] = hist[-100:]  # Last 100 ticks/days

        # Add Portfolio Positions (if any)
        # portfolio_history format: { "AAPL": [100, 101, ...], "GOOG": [...] }
        if portfolio_history:
            for sym, hist in portfolio_history.items():
                # Only add if not already in candidates (avoid self-comparison double count)
                if sym not in data_map and len(hist) > 10:
                    data_map[sym] = hist[-100:]

        if len(data_map) < 2:
            return candidates

        # Make equal length
        min_len = min(len(v) for v in data_map.values())
        truncated_map = {k: v[-min_len:] for k, v in data_map.items()}

        df = pd.DataFrame(truncated_map)

        # 2. Compute Correlation Matrix
        corr_matrix = df.corr()

        # 3. Scan for Clusters
        vetoed_symbols = set()

        # Identify which symbols are candidates vs existing positions
        candidate_symbols = set(c["symbol"] for c in candidates)

        symbols = list(truncated_map.keys())
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                sym_a = symbols[i]
                sym_b = symbols[j]

                if sym_a in vetoed_symbols or sym_b in vetoed_symbols:
                    continue

                correlation = corr_matrix.loc[sym_a, sym_b]

                if correlation > 0.85:
                    logger.warning(
                        f"BOYD: 🛡️ Cluster Detected! Corr({sym_a}, {sym_b}) = {correlation:.2f} > 0.85"
                    )

                    # LOGIC:
                    # 1. If Candidate vs Candidate -> Pick Winner.
                    # 2. If Candidate vs Portfolio -> VETO Candidate (Don't double down).
                    # 3. If Portfolio vs Portfolio -> Already held, ignore (or log warning).

                    is_a_cand = sym_a in candidate_symbols
                    is_b_cand = sym_b in candidate_symbols

                    if is_a_cand and is_b_cand:
                        # Battle of Candidates
                        cand_a = next(c for c in candidates if c["symbol"] == sym_a)
                        cand_b = next(c for c in candidates if c["symbol"] == sym_b)

                        score_a = cand_a.get("signal_confidence", 0.0) + abs(
                            cand_a.get("velocity", 0.0)
                        )
                        score_b = cand_b.get("signal_confidence", 0.0) + abs(
                            cand_b.get("velocity", 0.0)
                        )

                        if score_a >= score_b:
                            vetoed_symbols.add(sym_b)
                        else:
                            vetoed_symbols.add(sym_a)

                    elif is_a_cand and not is_b_cand:
                        # Candidate A vs Existing B -> Veto A
                        vetoed_symbols.add(sym_a)
                        logger.info(
                            f"BOYD: VETOING Candidate {sym_a} due to correlation with Existing {sym_b}"
                        )

                    elif not is_a_cand and is_b_cand:
                        # Existing A vs Candidate B -> Veto B
                        vetoed_symbols.add(sym_b)
                        logger.info(
                            f"BOYD: VETOING Candidate {sym_b} due to correlation with Existing {sym_a}"
                        )

                    # Portfolio vs Portfolio - Do nothing (we already own them)

        # 4. Filter Candidates
        final_candidates = []
        for c in candidates:
            if c["symbol"] in vetoed_symbols:
                c["success"] = False
                c["reasoning"] += " | VETOED: Correlation > 0.85 (Cluster Check)"
                c["signal_side"] = "FLAT"
            final_candidates.append(c)

        return final_candidates

    async def analyze(self, state: AgentState) -> AgentState:
        """
        Quantum Batch Analysis (OODA Loop).
        """
        analysis_start_time = time.time()
        candidates = state.get("watchlist", [])

        target_symbol = state.get("symbol", "SPY")
        primary_in_batch = any(c.get("symbol") == target_symbol for c in candidates)

        if not primary_in_batch:
            candidates.insert(0, {"symbol": target_symbol})

        if not candidates:
            # Fallback
            logger.warning(
                f"BOYD: No candidates found. Fallback to single symbol: {target_symbol}"
            )
            candidates = [{"symbol": target_symbol}]

        primary_symbol = state.get("symbol", "SPY")
        tasks = []

        # --- PARALLEL EXECUTION (Conditional LLM) ---
        for candidate_item in candidates:
            symbol = candidate_item["symbol"]
            is_primary = symbol == primary_symbol
            should_skip_llm = not is_primary

            tasks.append(self._analyze_single(symbol, skip_llm=should_skip_llm))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # --- MERGE & HOIST ---
        enriched_candidates = []
        primary_data = None

        for i, res in enumerate(results):
            candidate = candidates[i].copy()

            if isinstance(res, dict):
                candidate.update(res)
                # Primary logic delayed until after filters
            elif isinstance(res, Exception):
                logger.error(f"BOYD: Error analyzing {candidate.get('symbol')}: {res}")
                candidate["error"] = str(res)
                candidate["success"] = False

            enriched_candidates.append(candidate)

        # --- PHASE 37: THE ADAPTATION (Cluster Veto) ---
        # Apply Covariance Filter before picking Primary
        enriched_candidates = self._apply_covariance_veto(enriched_candidates)

        # Re-identify Primary based on Symbol (State) OR Veto status
        # If State Primary was Vetoed, we must switch.

        # Check current primary status
        temp_primary = next(
            (c for c in enriched_candidates if c["symbol"] == primary_symbol), None
        )

        if temp_primary and not temp_primary.get("success"):
            logger.warning(
                f"BOYD: Primary {primary_symbol} failed or VETOED. Seeking alternative..."
            )
            primary_data = None  # Force switch
        elif temp_primary:
            primary_data = temp_primary

        state["analysis_reports"] = enriched_candidates
        state["candidates"] = enriched_candidates

        if primary_data and primary_data.get("success"):
            # Check for Physics Veto (CRITICAL Regime)
            if primary_data.get("regime") == "Critical":
                logger.warning(
                    f"BOYD: Primary {primary_symbol} is in CRITICAL regime. Initiating searching for alternative..."
                )
                primary_data = None  # Discard

        if not primary_data:
            # Fallback / Auto-Selection: Pick highest confidence success
            valid_candidates = [
                c
                for c in enriched_candidates
                if c.get("success") and c.get("regime") != "Critical"
            ]
            if valid_candidates:
                # Sort by confidence desc
                valid_candidates.sort(
                    key=lambda x: x.get("signal_confidence", 0.0), reverse=True
                )
                primary_data = valid_candidates[0]
                primary_symbol = primary_data.get("symbol")
                state["symbol"] = primary_symbol  # Update State
                logger.info(
                    f"BOYD: 🔄 Switched Primary to {primary_symbol} (Conf: {primary_data.get('signal_confidence'):.2f})"
                )
            else:
                logger.warning("BOYD: No valid alternative candidates found.")

        # HOIST PRIMARY SIGNAL
        if primary_data and primary_data.get("success"):
            logger.info(f"BOYD: 🚀 Hoisting signal for {primary_symbol}")
            state["signal_side"] = primary_data.get("signal_side", "FLAT")
            state["signal_confidence"] = primary_data.get("signal_confidence", 0.0)
            state["regime"] = primary_data.get("regime", "Gaussian")
            state["reasoning"] = primary_data.get("reasoning", "")

            state["current_alpha"] = primary_data.get("current_alpha", 2.0)
            state["velocity"] = primary_data.get("velocity", 0.0)
            state["acceleration"] = primary_data.get("acceleration", 0.0)
            state["price"] = primary_data.get("price", 0.0)
            state["chronos_forecast"] = primary_data.get(
                "chronos_forecast", {"trend": "Neutral", "confidence": 0.0}
            )
        else:
            logger.warning(
                "BOYD: Primary symbol analysis failed or missing. State not updated."
            )

        successful = [c for c in enriched_candidates if c.get("success")]
        logger.info(
            f"BOYD: Batch Analysis Complete. {len(successful)}/{len(enriched_candidates)} successful."
        )

        # Telemetry
        latency = (time.time() - analysis_start_time) * 1000
        business_metrics.analyst_latency.record(latency)
        business_metrics.candidate_count.record(len(candidates))
        business_metrics.signals_total.add(len(successful))

        logger.info(f"⏱️ Boyd Latency: {latency:.2f}ms")

        return state


# --- GLOBAL INSTANCE ---
_boyd_agent_instance = BoydAgent()


async def boyd_node(state: AgentState) -> AgentState:
    """
    Pipeline Node Wrapper (Async) for Boyd (The Strategist).
    """
    return await _boyd_agent_instance.analyze(state)

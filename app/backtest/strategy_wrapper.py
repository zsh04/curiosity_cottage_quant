"""
Analyst Agent Strategy Wrapper for Backtesting

This module wraps the live AnalystAgent for use in the backtest engine by:
1. Injecting historical market data at each timestep
2. Mocking external dependencies (news, sentiment, LLM if needed)
3. Extracting signals from agent state

This enables "time travel" - treating historical data as if it were live.
"""

import logging
from typing import Optional, List
from unittest.mock import patch


from app.backtest.events import MarketEvent, SignalEvent
from app.backtest.strategy import Strategy
from app.agent.nodes.analyst import AnalystAgent
from app.agent.state import AgentState


logger = logging.getLogger(__name__)


class AnalystStrategy(Strategy):
    """Backtest wrapper for AnalystAgent to enable time-travel simulation.

    Acts as a bridge between the event-driven backtester and the production AnalystAgent.

    Key Features:
    - **Time Travel**: Injects historical price/volume data as if it were live.
    - **Dependency Mocking**: Patches external APIs (news, sentiment, LLM) to avoid
      calls during backtest and ensure determinism.
    - **State Management**: Maintains a rolling buffer of price history to calculate returns.

    Attributes:
        agent (AnalystAgent): The production agent instance being tested.
        mock_llm (bool): If True, uses a heuristic instead of calling Ollama (speed).
        mock_sentiment (bool): If True, bypasses FinBERT analysis.
        price_history (List[float]): Rolling buffer of closing prices.
    """

    def __init__(
        self,
        mock_llm: bool = True,
        mock_sentiment: bool = True,
        lookback_bars: int = 100,
    ):
        self.agent = AnalystAgent()
        self.mock_llm = mock_llm
        self.mock_sentiment = mock_sentiment
        self.lookback_bars = lookback_bars

        # Price history buffer (for historic_returns)
        self.price_history: List[float] = []
        self.timestamp_history: List = []

        # Track position state
        self.current_position = 0  # 0 = flat, 1 = long

        logger.info(
            f"🧪 AnalystStrategy initialized "
            f"(mock_llm={mock_llm}, mock_sentiment={mock_sentiment})"
        )

    def calculate_signals(self, event: MarketEvent, event_queue):
        """Main backtest entry point: Wraps agent analysis with mocked state.

        Process:
        1.  Updates internal price history buffer.
        2.  Constructs an `AgentState` object using historical context.
        3.  Monkey-patches `market`, `sentiment`, and `llm` adapters.
        4.  Executes `AnalystAgent.analyze()`.
        5.  Converts the agent's output signal to a backtest `SignalEvent`.

        Args:
            event (MarketEvent): The current market data bar.
            event_queue (queue.Queue): Queue to post generated signals to.
        """
        if event.type != "MARKET":
            return

        # Update history
        self.price_history.append(event.close)
        self.timestamp_history.append(event.timestamp)

        # Keep only recent data
        if len(self.price_history) > self.lookback_bars:
            self.price_history.pop(0)
            self.timestamp_history.pop(0)

        # Need minimum history for analysis
        if len(self.price_history) < 30:
            logger.debug(f"⏳ Warming up: {len(self.price_history)}/30 bars")
            return

        # Construct AgentState
        state = self._construct_agent_state(event)

        # Monkey-patch external dependencies
        with self._mock_external_dependencies(event):
            try:
                # Run analyst agent
                logger.debug(
                    f"🧠 Running AnalystAgent for {event.symbol} @ ${event.close:.2f}"
                )
                state = self.agent.analyze(state)

                # Extract signal
                signal_side = state.get("signal_side", "FLAT")
                signal_confidence = state.get("signal_confidence", 0.0)

                # Convert to SignalEvent
                signal_event = self._convert_to_signal_event(
                    event, signal_side, signal_confidence
                )

                if signal_event:
                    event_queue.put(signal_event)
                    logger.info(
                        f"📡 Signal: {signal_side} {event.symbol} "
                        f"(confidence: {signal_confidence:.2f})"
                    )

            except Exception as e:
                logger.error(f"❌ BoydAgent failed: {e}", exc_info=True)

    def _construct_agent_state(self, event: MarketEvent) -> AgentState:
        """
        Construct AgentState from historical data.

        Provides the agent with context as if running live.
        """
        # Calculate returns from price history
        historic_returns = []
        for i in range(1, len(self.price_history)):
            ret = (self.price_history[i] / self.price_history[i - 1]) - 1.0
            historic_returns.append(ret)

        # Initial state
        state = AgentState(
            symbol=event.symbol,
            price=event.close,
            historic_returns=historic_returns,
            cash=100000.0,  # Placeholder, portfolio manages this
            regime="Unknown",  # Will be determined by macro node
            status="ACTIVE",
            messages=[],
        )

        return state

    def _mock_external_dependencies(self, event: MarketEvent):
        """
        Context manager to mock external dependencies during backtest.

        Patches:
        - market.get_current_price() -> event.close
        - market.get_news() -> [] or historical news
        - sentiment.analyze() -> neutral
        - llm.predict() -> heuristic (if mock_llm=True)
        """
        patches = []

        # Mock market adapter methods
        def mock_get_current_price(symbol):
            return event.close

        def mock_get_historic_returns(symbol, lookback=100):
            # Already have this in price_history
            returns = []
            for i in range(1, min(len(self.price_history), lookback + 1)):
                ret = (
                    (self.price_history[-i] / self.price_history[-i - 1]) - 1.0
                    if i < len(self.price_history)
                    else 0.0
                )
                returns.append(ret)
            return list(reversed(returns))

        def mock_get_news(symbol, limit=5):
            # Generate synthetic news based on price action to exercise FinBERT
            # Get today's return
            if len(self.price_history) >= 2:
                daily_ret = (self.price_history[-1] / self.price_history[-2]) - 1.0
            else:
                daily_ret = 0.0

            headlines = []
            if daily_ret > 0.01:
                headlines.append(
                    {
                        "title": f"{symbol} soars as market sentiment improves",
                        "url": "http://mock.url",
                        "publishedDate": "2025-01-01",
                    }
                )
                headlines.append(
                    {
                        "title": "Analysts upgrade growth outlook",
                        "url": "http://mock.url",
                        "publishedDate": "2025-01-01",
                    }
                )
            elif daily_ret < -0.01:
                headlines.append(
                    {
                        "title": f"{symbol} drops amidst recession fears",
                        "url": "http://mock.url",
                        "publishedDate": "2025-01-01",
                    }
                )
                headlines.append(
                    {
                        "title": "Inflation concerns weigh on markets",
                        "url": "http://mock.url",
                        "publishedDate": "2025-01-01",
                    }
                )
            else:
                headlines.append(
                    {
                        "title": f"{symbol} trades flat in quiet session",
                        "url": "http://mock.url",
                        "publishedDate": "2025-01-01",
                    }
                )

            return headlines

        patches.append(
            patch.object(
                self.agent.market,
                "get_current_price",
                side_effect=mock_get_current_price,
            )
        )

        patches.append(
            patch.object(
                self.agent.market,
                "get_historic_returns",
                side_effect=mock_get_historic_returns,
            )
        )

        patches.append(
            patch.object(self.agent.market, "get_news", side_effect=mock_get_news)
        )

        # Mock sentiment if requested
        if self.mock_sentiment:

            def mock_sentiment_analyze(text):
                return {"sentiment": "neutral", "score": 0.0, "error": None}

            patches.append(
                patch.object(
                    self.agent.sentiment, "analyze", side_effect=mock_sentiment_analyze
                )
            )

        # Mock LLM if requested (fast backtest mode)
        if self.mock_llm:

            def mock_get_trade_signal(prompt, **kwargs):
                # Simple heuristic: BUY if velocity > 0, SELL otherwise
                # Extract velocity from prompt if available
                if "Velocity" in prompt:
                    # Parse velocity (crude heuristic)
                    try:
                        velocity_line = [
                            line for line in prompt.split("\n") if "Velocity" in line
                        ][0]
                        velocity = float(velocity_line.split(":")[-1].strip())

                        if velocity > 0.0001:
                            signal_side = "BUY"
                            confidence = min(abs(velocity) * 10, 1.0)
                        elif velocity < -0.0001:
                            signal_side = "SELL"
                            confidence = min(abs(velocity) * 10, 1.0)
                        else:
                            signal_side = "FLAT"
                            confidence = 0.5
                    except Exception:
                        signal_side = "FLAT"
                        confidence = 0.5
                else:
                    signal_side = "FLAT"
                    confidence = 0.5

                # Mock LLM response
                return {
                    "signal_side": signal_side,
                    "signal_confidence": confidence,
                    "reasoning": "Mock LLM heuristic based on velocity",
                    # Add dummy tokens for saving metrics in AnalystAgent
                    "tokens_input": 100,
                    "tokens_output": 20,
                    "raw_response": "Mocked response",
                }

            patches.append(
                patch.object(
                    self.agent.llm,
                    "get_trade_signal",
                    side_effect=mock_get_trade_signal,
                )
            )

        # Stack all context managers
        from contextlib import ExitStack

        stack = ExitStack()
        for p in patches:
            stack.enter_context(p)

        return stack

    def _convert_to_signal_event(
        self, event: MarketEvent, signal_side: str, signal_confidence: float
    ) -> Optional[SignalEvent]:
        """
        Convert agent signal to backtest SignalEvent.

        Args:
            event: Current market event
            signal_side: Agent signal (BUY/SELL/FLAT)
            signal_confidence: Confidence score

        Returns:
            SignalEvent or None if no action needed
        """
        # Map agent signals to backtest signals
        if signal_side == "BUY" and self.current_position == 0:
            # Open long position
            self.current_position = 1
            return SignalEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                direction="LONG",
                strength=signal_confidence,
            )

        elif signal_side == "SELL" and self.current_position == 1:
            # Close long position
            self.current_position = 0
            return SignalEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                direction="EXIT",
                strength=signal_confidence,
            )

        elif signal_side == "FLAT" and self.current_position == 1:
            # Agent recommends flat but we're long - exit
            self.current_position = 0
            return SignalEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                direction="EXIT",
                strength=0.5,
            )

        # No action needed
        return None

    def get_agent_state(self) -> dict:
        """
        Get current agent internal state for inspection.

        Returns:
            Dictionary with agent state metrics
        """
        return {
            "price_history_len": len(self.price_history),
            "current_position": self.current_position,
            "mock_llm": self.mock_llm,
            "mock_sentiment": self.mock_sentiment,
        }

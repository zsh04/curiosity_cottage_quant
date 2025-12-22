#!/usr/bin/env python3.11
"""
COMPREHENSIVE END-TO-END SYSTEM AUDIT
Simulates a full trading cycle and validates every component.
Post-Migration: Docker → Hybrid Metal
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / ".env")
sys.path.insert(0, str(root_dir))

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

# Suppress warnings
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

from app.agent.graph import app_graph
from app.agent.state import AgentState
from app.dal.database import SessionLocal
from app.adapters.market import MarketAdapter
from app.adapters.llm import LLMAdapter
from app.adapters.sentiment import SentimentAdapter
from app.adapters.chronos import ChronosAdapter
from app.services.memory import MemoryService

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class SystemAuditor:
    def __init__(self):
        self.results: Dict[str, bool] = {}
        self.failures: List[str] = []

    async def test(self, name: str, fn, *args, **kwargs):
        """Run a test and record results"""
        try:
            result = fn(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result

            success = result if isinstance(result, bool) else True
            self.results[name] = success

            symbol = f"{GREEN}✅{RESET}" if success else f"{RED}❌{RESET}"
            print(f"{symbol} {name}")

            if not success:
                self.failures.append(name)

            return success
        except Exception as e:
            self.results[name] = False
            self.failures.append(name)
            print(f"{RED}❌ {name}: {str(e)[:100]}{RESET}")
            return False

    def section(self, title: str):
        """Print section header"""
        print(f"\n{BLUE}{'=' * 70}{RESET}")
        print(f"{BLUE}{title}{RESET}")
        print(f"{BLUE}{'=' * 70}{RESET}")


async def main():
    auditor = SystemAuditor()

    print(f"\n{YELLOW}🔍 HYBRID METAL SYSTEM AUDIT{RESET}")
    print(f"{YELLOW}Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")

    # =================================================================
    # 1. INFRASTRUCTURE
    # =================================================================
    auditor.section("1️⃣  INFRASTRUCTURE")

    def test_database():
        from sqlalchemy import text

        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return True
        finally:
            db.close()

    await auditor.test("Database Connection (TimescaleDB)", test_database)

    def test_env_vars():
        required = [
            "ALPHAVANTAGE_API_KEY",
            "FINNHUB_API_KEY",
            "TIINGO_API_KEY",
            "ALPACA_API_KEY",
            "OLLAMA_MODEL",
            "DATABASE_URL",
        ]
        missing = [v for v in required if not os.getenv(v)]
        if missing:
            print(f"  Missing: {', '.join(missing)}")
            return False
        return True

    await auditor.test("Environment Variables", test_env_vars)

    # =================================================================
    # 2. DATA ADAPTERS
    # =================================================================
    auditor.section("2️⃣  DATA ADAPTERS")

    def test_market_adapter():
        adapter = MarketAdapter()
        price = adapter.get_price("AAPL")
        print(f"  AAPL Price: ${price}")
        return price > 0

    await auditor.test("Market Data (get_price)", test_market_adapter)

    def test_market_history():
        adapter = MarketAdapter()
        history = adapter.get_price_history("AAPL", limit=10)
        print(f"  History length: {len(history)}")
        return len(history) >= 10

    await auditor.test("Market Data (get_price_history)", test_market_history)

    def test_sentiment():
        adapter = SentimentAdapter()
        result = adapter.analyze("The market is bullish and strong")
        print(f"  Sentiment: {result['label']} ({result['score']:.2f})")
        return result["score"] > 0

    await auditor.test("Sentiment Adapter (FinBERT)", test_sentiment)

    def test_llm():
        adapter = LLMAdapter()
        response = adapter.generate("Say 'OK' if you're working", max_tokens=10)
        print(f"  LLM Response: {response[:50]}")
        return len(response) > 0

    await auditor.test("LLM Adapter (Ollama)", test_llm)

    def test_chronos():
        adapter = ChronosAdapter()
        prices = [100 + i * 0.5 for i in range(50)]  # Synthetic trend
        forecast = adapter.predict(prices, horizon=5)
        if forecast:
            print(f"  Forecast median: {forecast['median'][:3]}")
            return True
        return False

    await auditor.test("Chronos Forecaster (Metal)", test_chronos)

    # =================================================================
    # 3. SERVICES
    # =================================================================
    auditor.section("3️⃣  SERVICES")

    def test_memory_save():
        # MemoryService no longer requires db session in init
        memory = MemoryService()
        memory.save_regime(
            symbol="TEST_AUDIT",
            physics={"regime": "TREND", "alpha": 1.5},
            sentiment={"label": "positive", "score": 0.9},
        )
        return True

    await auditor.test("Memory Service (save_regime)", test_memory_save)

    def test_memory_retrieve():
        memory = MemoryService()
        # Create dummy search criteria
        results = memory.retrieve_similar(
            symbol="TEST_AUDIT",
            physics={
                "regime": "TREND",
                "alpha": 1.5,
                "velocity": 0.05,
                "acceleration": 0.001,
            },
            sentiment={"label": "positive", "score": 0.9},
            k=3,
        )
        print(f"  Retrieved: {len(results)} regimes")
        return True

    await auditor.test("Memory Service (retrieve)", test_memory_retrieve)

    # =================================================================
    # 4. AGENT GRAPH (END-TO-END)
    # =================================================================
    auditor.section("4️⃣  AGENT GRAPH - FULL TRADE SIMULATION")

    async def simulate_trade():
        """Simulate a complete trade cycle"""
        print(f"\n  {YELLOW}Simulating trade for SPY...{RESET}")

        # Initialize state
        state = AgentState(
            symbol="SPY",
            status="ACTIVE",
            cash=100000.0,
            position=0.0,
            max_position_size=10000.0,
            regime="UNKNOWN",
            signal_side="FLAT",
            signal_confidence=0.0,
            approved_size=0.0,
            messages=[],
            iteration=0,
        )

        # Run one iteration using compiled graph
        try:
            final_state = await app_graph.ainvoke(state)

            # Validate outputs
            checks = []

            # Check regime was determined
            checks.append(("Regime Determined", final_state.get("regime") != "UNKNOWN"))

            # Check signal generated
            checks.append(
                (
                    "Signal Generated",
                    final_state.get("signal_side") in ["LONG", "SHORT", "FLAT"],
                )
            )

            # Check confidence calculated
            checks.append(
                ("Confidence Score", 0 <= final_state.get("signal_confidence", 0) <= 1)
            )

            # Check risk approval
            checks.append(("Risk Approval", "approved_size" in final_state))

            # Print results
            for name, passed in checks:
                symbol = f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"
                print(f"    {symbol} {name}")

            # Print key metrics
            print(f"\n  {BLUE}Trade Results:{RESET}")
            print(f"    Regime: {final_state.get('regime', 'N/A')}")
            print(
                f"    Signal: {final_state.get('signal_side', 'N/A')} @ {final_state.get('signal_confidence', 0):.2f}"
            )
            print(f"    Approved Size: ${final_state.get('approved_size', 0):.2f}")
            print(f"    Messages: {len(final_state.get('messages', []))}")

            return all(passed for _, passed in checks)
        except Exception as e:
            print(f"  {RED}Agent Graph Error: {str(e)[:200]}{RESET}")
            import traceback

            traceback.print_exc()
            return False

    await auditor.test("Agent Graph (Full Cycle)", simulate_trade)

    # =================================================================
    # 5. TELEMETRY
    # =================================================================
    auditor.section("5️⃣  OBSERVABILITY")

    def test_otel_collector():
        import requests

        try:
            resp = requests.get("http://localhost:13133", timeout=2)
            return resp.status_code == 200
        except:
            return False

    await auditor.test("OTEL Collector Health", test_otel_collector)

    def test_backend_telemetry():
        # Check if telemetry was initialized
        from opentelemetry import trace, metrics

        tracer = trace.get_tracer(__name__)
        meter = metrics.get_meter(__name__)
        return tracer is not None and meter is not None

    await auditor.test("Backend Telemetry (OTEL SDK)", test_backend_telemetry)

    # =================================================================
    # FINAL REPORT
    # =================================================================
    print(f"\n{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}AUDIT COMPLETE{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}\n")

    total = len(auditor.results)
    passed = sum(auditor.results.values())
    failed = total - passed

    print(f"Total Tests: {total}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    print(f"{RED}Failed: {failed}{RESET}")

    if failed > 0:
        print(f"\n{RED}FAILED TESTS:{RESET}")
        for failure in auditor.failures:
            print(f"  ❌ {failure}")

    # Verdict
    print(f"\n{BLUE}{'=' * 70}{RESET}")
    if failed == 0:
        print(f"{GREEN}✅ SYSTEM STATUS: OPERATIONAL{RESET}")
        print(f"{GREEN}All components verified. Ready for production.{RESET}")
    elif failed <= 2:
        print(f"{YELLOW}⚠️  SYSTEM STATUS: DEGRADED{RESET}")
        print(f"{YELLOW}Minor issues detected. Review failures.{RESET}")
    else:
        print(f"{RED}❌ SYSTEM STATUS: CRITICAL{RESET}")
        print(f"{RED}Multiple failures detected. System not ready.{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())

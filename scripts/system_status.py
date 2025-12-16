#!/usr/bin/env python3
"""
System Status Check - Pre-Flight Diagnostic for CC-V2
Comprehensive health verification before live trading.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.dal.database import get_db
from app.dal.models import MarketTick, MacroTick, AgentStateSnapshot
from app.adapters.llm import LLMAdapter
from app.adapters.chronos import ChronosAdapter
from app.adapters.sentiment import SentimentAdapter
from app.adapters.market import MarketAdapter


class SystemHealthCheck:
    """Comprehensive system health verification with strict SRE standards."""

    def __init__(self):
        self.db: Session = next(get_db())
        self.llm = LLMAdapter()
        self.chronos = ChronosAdapter()
        self.sentiment = SentimentAdapter()
        self.market = MarketAdapter()

        self.results = []  # Store (emoji, name, message) tuples
        self.critical_failures = 0
        self.warnings = 0

    def log_result(self, emoji: str, name: str, message: str, critical: bool = True):
        """Log a test result."""
        self.results.append((emoji, name, message))
        if emoji == "🔴" and critical:
            self.critical_failures += 1
        elif emoji == "🟡":
            self.warnings += 1

    def print_header(self):
        """Print header."""
        print("\n" + "=" * 80)
        print("🚀 CC-V2 PRE-FLIGHT DIAGNOSTIC")
        print("=" * 80)
        print(
            f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        print("=" * 80 + "\n")

    # ========== SECTION 1: MICROSERVICE PINGS ==========

    def test_brain(self):
        """Test Ollama/Gemma2 (Brain)."""
        try:
            if self.llm.health_check():
                self.log_result("🟢", "Brain (Gemma2)", "Model loaded and ready")
            else:
                self.log_result(
                    "🔴", "Brain (Gemma2)", "Service unreachable or model not loaded"
                )
        except Exception as e:
            self.log_result("🔴", "Brain (Gemma2)", f"Error: {e}")

    def test_eyes(self):
        """Test Chronos forecasting (Eyes)."""
        try:
            if self.chronos.health_check():
                self.log_result("🟢", "Eyes (Chronos)", "Forecasting service online")
            else:
                self.log_result(
                    "🟡",
                    "Eyes (Chronos)",
                    "Service offline (non-critical)",
                    critical=False,
                )
        except Exception as e:
            self.log_result(
                "🟡", "Eyes (Chronos)", f"Error: {e} (non-critical)", critical=False
            )

    def test_gut(self):
        """Test FinBERT sentiment (Gut)."""
        try:
            if self.sentiment.health_check():
                self.log_result("🟢", "Gut (FinBERT)", "Sentiment analysis ready")
            else:
                self.log_result(
                    "🟡",
                    "Gut (FinBERT)",
                    "Service offline (non-critical)",
                    critical=False,
                )
        except Exception as e:
            self.log_result(
                "🟡", "Gut (FinBERT)", f"Error: {e} (non-critical)", critical=False
            )

    def test_nerves(self):
        """Test Tiingo/Alpaca news API (Nerves)."""
        try:
            news = self.market.get_news("SPY", limit=1)
            if news and len(news) > 0:
                self.log_result(
                    "🟢", "Nerves (News API)", f"Fetched {len(news)} headline(s)"
                )
            else:
                self.log_result(
                    "🟡",
                    "Nerves (News API)",
                    "No news available (non-critical)",
                    critical=False,
                )
        except Exception as e:
            self.log_result(
                "🟡", "Nerves (News API)", f"Error: {e} (non-critical)", critical=False
            )

    def section_1_microservices(self):
        """Test all microservices."""
        print("🏥 SECTION 1: MICROSERVICE HEALTH (The Organs)")
        print("-" * 80)

        self.test_brain()
        self.test_eyes()
        self.test_gut()
        self.test_nerves()

        print()

    # ========== SECTION 2: DATABASE VITALS ==========

    def test_database_connection(self):
        """Test database connection."""
        try:
            result = self.db.execute(text("SELECT 1")).scalar()
            if result == 1:
                self.log_result("🟢", "Database (Postgres)", "Connection healthy")
            else:
                self.log_result(
                    "🔴", "Database (Postgres)", "Query returned unexpected result"
                )
        except Exception as e:
            self.log_result("🔴", "Database (Postgres)", f"Connection failed: {e}")

    def test_market_data_freshness(self):
        """Test market data freshness."""
        try:
            latest_tick = (
                self.db.query(MarketTick)
                .filter(MarketTick.symbol == "SPY")
                .order_by(MarketTick.time.desc())
                .first()
            )

            if latest_tick:
                now = datetime.now(timezone.utc)
                age = now - latest_tick.time.replace(tzinfo=timezone.utc)

                # Check market hours (9:30 AM - 4:00 PM ET, roughly 14:30-21:00 UTC)
                hour_utc = now.hour
                is_market_hours = 14 <= hour_utc <= 21 and now.weekday() < 5

                if is_market_hours and age > timedelta(minutes=5):
                    self.log_result(
                        "🟡",
                        "Market Data (SPY)",
                        f"Stale: {age.seconds // 60}m old (market hours)",
                        critical=False,
                    )
                elif age > timedelta(hours=24):
                    self.log_result(
                        "🟡",
                        "Market Data (SPY)",
                        f"Stale: {age.days}d old",
                        critical=False,
                    )
                else:
                    self.log_result(
                        "🟢", "Market Data (SPY)", f"Fresh: {age.seconds // 60}m ago"
                    )
            else:
                self.log_result(
                    "🟡", "Market Data (SPY)", "No ticks available", critical=False
                )
        except Exception as e:
            self.log_result("🟡", "Market Data (SPY)", f"Error: {e}", critical=False)

    def test_physics_state(self):
        """Test physics state snapshot."""
        try:
            latest = (
                self.db.query(AgentStateSnapshot)
                .order_by(AgentStateSnapshot.timestamp.desc())
                .first()
            )

            if latest:
                alpha = latest.current_alpha or 3.0
                regime = latest.regime or "Unknown"
                self.log_result(
                    "🟢", "Physics State", f"Alpha={alpha:.2f}, Regime={regime}"
                )
            else:
                self.log_result(
                    "🟡", "Physics State", "No snapshots available", critical=False
                )
        except Exception as e:
            self.log_result("🟡", "Physics State", f"Error: {e}", critical=False)

    def section_2_database(self):
        """Test database vitals."""
        print("💾 SECTION 2: DATABASE VITALS (The Blood)")
        print("-" * 80)

        self.test_database_connection()
        self.test_market_data_freshness()
        self.test_physics_state()

        print()

    # ========== SECTION 3: COGNITIVE STIMULUS TESTS ==========

    def test_sentiment_stimulus(self):
        """Test sentiment analysis with known-good input."""
        try:
            test_text = "Apple posts record profits and beats earnings expectations"
            result = self.sentiment.analyze(test_text)

            if result and not result.get("error"):
                label = result.get("sentiment", "unknown").lower()
                score = result.get("score", 0.0)

                # Expect positive sentiment
                if label in ["positive", "pos"]:
                    self.log_result(
                        "🟢",
                        "Sentiment Stimulus",
                        f"Correctly identified 'positive' (score: {score:.2f})",
                    )
                else:
                    self.log_result(
                        "🟡",
                        "Sentiment Stimulus",
                        f"Expected positive, got '{label}' (score: {score:.2f})",
                        critical=False,
                    )
            else:
                self.log_result(
                    "🔴", "Sentiment Stimulus", "Failed to analyze test text"
                )
        except Exception as e:
            self.log_result("🔴", "Sentiment Stimulus", f"Error: {e}")

    def test_forecast_stimulus(self):
        """Test forecasting with dummy price sequence."""
        try:
            # Simple uptrend sequence
            dummy_prices = [100.0 + i * 0.5 for i in range(20)]
            forecast = self.chronos.predict(dummy_prices, horizon=5)

            if forecast and forecast.get("median"):
                forecast_len = len(forecast["median"])
                self.log_result(
                    "🟢",
                    "Forecast Stimulus",
                    f"Generated {forecast_len} forecast points",
                )
            else:
                self.log_result(
                    "🟡", "Forecast Stimulus", "No forecast returned", critical=False
                )
        except Exception as e:
            self.log_result("🟡", "Forecast Stimulus", f"Error: {e}", critical=False)

    def section_3_cognitive(self):
        """Run cognitive stimulus tests."""
        print("🧠 SECTION 3: COGNITIVE STIMULUS TESTS (The Mind)")
        print("-" * 80)

        self.test_sentiment_stimulus()
        self.test_forecast_stimulus()

        print()

    # ========== FINAL REPORT ==========

    def print_summary(self):
        """Print comprehensive summary table."""
        print("=" * 80)
        print("📊 DIAGNOSTIC SUMMARY")
        print("=" * 80)

        # Print all results in table format
        for emoji, name, message in self.results:
            print(f"{emoji}  {name:<25} | {message}")

        print("=" * 80)
        print(f"Critical Failures: {self.critical_failures} 🔴")
        print(f"Warnings:          {self.warnings} 🟡")
        print(f"Total Checks:      {len(self.results)}")
        print("=" * 80)

    def print_verdict(self) -> bool:
        """Print final verdict."""
        if self.critical_failures == 0:
            print("\n🚀 SYSTEM STATUS: READY")
            print("All critical systems operational. Cleared for live trading.\n")
            return True
        else:
            print(f"\n🚨 SYSTEM STATUS: ABORT")
            print(f"Critical failures detected: {self.critical_failures}")
            print("System is NOT ready for live trading.\n")
            return False

    def run(self) -> bool:
        """Run all health checks."""
        try:
            self.print_header()
            self.section_1_microservices()
            self.section_2_database()
            self.section_3_cognitive()
            self.print_summary()
            return self.print_verdict()
        finally:
            self.db.close()


def main():
    """Main entry point."""
    try:
        checker = SystemHealthCheck()
        success = checker.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

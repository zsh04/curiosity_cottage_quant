"""
Full System Test: Quantile-Powered Risk Analytics

Tests the complete flow from Chronos quantiles → BrainService → Boyd → Taleb
Captures and displays risk metrics (VaR, ES, Confidence, R/R) in action.
"""

import asyncio
import logging
from app.agent.boyd import BoydAgent
from app.core.telemetry import init_telemetry

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


async def test_full_system():
    """Run full system test showing risk metrics in action."""

    logger.info("=" * 80)
    logger.info("🧪 FULL SYSTEM TEST: Quantile-Powered Risk Analytics")
    logger.info("=" * 80)

    # Initialize telemetry
    init_telemetry()

    # Create Boyd agent
    boyd = BoydAgent()

    # Test symbols
    test_symbols = ["AAPL", "MSFT", "TSLA"]

    for symbol in test_symbols:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"📊 Analyzing: {symbol}")
        logger.info(f"{'=' * 80}")

        try:
            # Run analysis (this will trigger full quantile flow)
            result = await boyd._analyze_single(symbol, skip_llm=True)

            # Display results
            logger.info(f"\n✅ Analysis Complete for {symbol}")
            logger.info(f"   Signal: {result.get('signal_side', 'N/A')}")
            logger.info(f"   Confidence: {result.get('signal_confidence', 0):.2%}")
            logger.info(f"   Price: ${result.get('price', 0):.2f}")
            logger.info(f"   Velocity: {result.get('velocity', 0):.4f}")
            logger.info(f"   Regime: {result.get('regime', 'N/A')}")
            logger.info(f"   Alpha: {result.get('current_alpha', 0):.2f}")

            # Display risk metrics (if available)
            risk_metrics = result.get("risk_metrics", {})
            if risk_metrics:
                logger.info(f"\n   📊 RISK METRICS:")

                var_data = risk_metrics.get("var", {})
                if var_data:
                    logger.info(f"      VaR (90%): {var_data.get('var_pct', 0):.2%}")
                    logger.info(
                        f"      VaR Absolute: ${var_data.get('var_absolute', 0):.2f}"
                    )

                es_data = risk_metrics.get("expected_shortfall", {})
                if es_data:
                    logger.info(f"      ES (90%): {es_data.get('es_pct', 0):.2%}")
                    logger.info(
                        f"      ES Absolute: ${es_data.get('es_absolute', 0):.2f}"
                    )
                    logger.info(
                        f"      Tail Quantiles: {es_data.get('tail_quantiles_count', 0)}"
                    )

                conf_data = risk_metrics.get("distributional_confidence", {})
                if conf_data:
                    logger.info(
                        f"      Forecast Confidence: {conf_data.get('confidence_score', 0):.2f}"
                    )
                    logger.info(f"      IQR: ${conf_data.get('iqr', 0):.2f}")
                    logger.info(f"      CV: {conf_data.get('cv', 0):.2f}")

                scenarios = risk_metrics.get("scenarios", {})
                if scenarios:
                    summary = scenarios.get("summary", {})
                    logger.info(
                        f"      Risk/Reward: {summary.get('risk_reward_ratio', 0):.2f}"
                    )
                    logger.info(
                        f"      Skewness: {summary.get('skewness_indicator', 0):.2f}"
                    )

                    logger.info(f"\n   📈 SCENARIOS:")
                    for name, data in scenarios.items():
                        if name != "summary" and isinstance(data, dict):
                            logger.info(
                                f"      {data.get('label', name)}: {data.get('return_pct', 0):.2%}"
                            )
            else:
                logger.warning(
                    f"   ⚠️ No risk metrics available (quantiles may be missing)"
                )

            # Display forecast
            forecast = result.get("chronos_forecast", {})
            quantiles = forecast.get("quantiles", [])
            logger.info(f"\n   🔮 FORECAST:")
            logger.info(f"      P10: ${forecast.get('p10', 0):.2f}")
            logger.info(f"      P50: ${forecast.get('p50', 0):.2f}")
            logger.info(f"      P90: ${forecast.get('p90', 0):.2f}")
            logger.info(f"      Trend: {forecast.get('trend', 0):.2%}")
            logger.info(f"      Quantiles: {len(quantiles)} values")

        except Exception as e:
            logger.error(f"❌ Analysis failed for {symbol}: {e}", exc_info=True)

    logger.info(f"\n{'=' * 80}")
    logger.info("✅ FULL SYSTEM TEST COMPLETE")
    logger.info(f"{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(test_full_system())

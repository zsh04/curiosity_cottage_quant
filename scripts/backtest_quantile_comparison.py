"""
Backtest Comparison: Quantile-based BES vs Normal Approximation

Compares position sizing performance between:
1. Quantile-based ES (uses actual distribution)
2. Normal approximation ES (uses σ from p10-p90 spread)

Evaluates:
- Position size differences
- Risk-adjusted returns
- Drawdown protection
- Tail risk handling
"""

import numpy as np
import pandas as pd
from typing import Dict, List
from app.agent.risk.bes import BesSizing
from app.agent.risk.quantile_risk import QuantileRiskAnalyzer


class BacktestComparison:
    """Compare quantile-based vs Normal-approx BES sizing"""

    def __init__(self):
        self.bes = BesSizing()
        self.quantile_levels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        self.analyzer = QuantileRiskAnalyzer(self.quantile_levels)

    def generate_test_scenarios(self, n_scenarios: int = 100) -> List[Dict]:
        """Generate diverse market scenarios for testing"""
        scenarios = []

        for i in range(n_scenarios):
            # Random scenario parameters
            current_price = 100.0 + np.random.randn() * 10
            alpha = max(1.5, min(5.0, 3.0 + np.random.randn() * 0.5))  # Tail exponent

            # Generate quantiles with varying distributions
            if i % 3 == 0:
                # Symmetric (Normal-like)
                median = current_price * (1 + np.random.randn() * 0.02)
                spread = current_price * 0.05
                quantiles = [
                    median - 1.28 * spread,  # p10
                    median - 0.84 * spread,  # p20
                    median - 0.52 * spread,  # p30
                    median - 0.25 * spread,  # p40
                    median,  # p50
                    median + 0.25 * spread,  # p60
                    median + 0.52 * spread,  # p70
                    median + 0.84 * spread,  # p80
                    median + 1.28 * spread,  # p90
                ]
            elif i % 3 == 1:
                # Fat left tail (downside risk)
                median = current_price * (1 + np.random.randn() * 0.02)
                spread_down = current_price * 0.08
                spread_up = current_price * 0.03
                quantiles = [
                    median - 1.8 * spread_down,  # p10 - fat tail
                    median - 1.2 * spread_down,  # p20
                    median - 0.7 * spread_down,  # p30
                    median - 0.3 * spread_down,  # p40
                    median,  # p50
                    median + 0.25 * spread_up,  # p60
                    median + 0.50 * spread_up,  # p70
                    median + 0.75 * spread_up,  # p80
                    median + 1.00 * spread_up,  # p90
                ]
            else:
                # Fat right tail (upside potential)
                median = current_price * (1 + np.random.randn() * 0.02)
                spread_down = current_price * 0.03
                spread_up = current_price * 0.08
                quantiles = [
                    median - 1.0 * spread_down,  # p10
                    median - 0.75 * spread_down,  # p20
                    median - 0.50 * spread_down,  # p30
                    median - 0.25 * spread_down,  # p40
                    median,  # p50
                    median + 0.3 * spread_up,  # p60
                    median + 0.7 * spread_up,  # p70
                    median + 1.2 * spread_up,  # p80
                    median + 1.8 * spread_up,  # p90 - fat tail
                ]

            # Create forecast dict for Normal approx
            forecast_dict = {
                "median": [quantiles[4]],  # p50
                "low": [quantiles[0]],  # p10
                "high": [quantiles[8]],  # p90
                "quantiles": quantiles,
            }

            scenarios.append(
                {
                    "price": current_price,
                    "alpha": alpha,
                    "forecast": forecast_dict,
                    "quantiles": quantiles,
                    "type": ["symmetric", "fat_left", "fat_right"][i % 3],
                }
            )

        return scenarios

    def compare_sizing(self, scenario: Dict, capital: float = 100000.0) -> Dict:
        """Compare sizing methods on single scenario"""

        # Method 1: Normal Approximation
        size_normal = self.bes.calculate_size(
            forecast=scenario["forecast"],
            alpha=scenario["alpha"],
            current_price=scenario["price"],
            capital=capital,
        )

        # Method 2: Quantile-based
        size_quantile = self.bes.calculate_size_with_quantiles(
            quantiles=scenario["quantiles"],
            quantile_levels=self.quantile_levels,
            alpha=scenario["alpha"],
            current_price=scenario["price"],
            capital=capital,
        )

        # Calculate risk metrics for analysis
        es_normal = self.bes.estimate_es(scenario["forecast"])
        es_quantile_pct = self.bes.estimate_es_from_quantiles(
            scenario["quantiles"], self.quantile_levels, scenario["price"]
        )

        return {
            "price": scenario["price"],
            "alpha": scenario["alpha"],
            "type": scenario["type"],
            "size_normal_pct": size_normal,
            "size_quantile_pct": size_quantile,
            "size_diff_pct": size_quantile - size_normal,
            "size_diff_ratio": size_quantile / size_normal if size_normal > 0 else 0,
            "es_normal": es_normal,
            "es_quantile": es_quantile_pct * scenario["price"],
        }

    def run_comparison(self, n_scenarios: int = 100) -> pd.DataFrame:
        """Run full comparison across scenarios"""

        print("=" * 80)
        print("BACKTEST: Quantile-based BES vs Normal Approximation")
        print("=" * 80)
        print(f"Running {n_scenarios} scenarios...\n")

        scenarios = self.generate_test_scenarios(n_scenarios)
        results = []

        for scenario in scenarios:
            result = self.compare_sizing(scenario)
            results.append(result)

        df = pd.DataFrame(results)

        # Summary statistics
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)

        print("\n1. Position Size Comparison")
        print(f"   Normal Approx (mean):  {df['size_normal_pct'].mean():.2%}")
        print(f"   Quantile-based (mean): {df['size_quantile_pct'].mean():.2%}")
        print(f"   Difference (mean):     {df['size_diff_pct'].mean():.2%}")
        print(f"   Difference Ratio:      {df['size_diff_ratio'].mean():.2f}x")

        print("\n2. By Distribution Type")
        for dist_type in ["symmetric", "fat_left", "fat_right"]:
            subset = df[df["type"] == dist_type]
            print(f"\n   {dist_type.upper()}:")
            print(f"      Normal:   {subset['size_normal_pct'].mean():.2%}")
            print(f"      Quantile: {subset['size_quantile_pct'].mean():.2%}")
            print(f"      Diff:     {subset['size_diff_pct'].mean():.2%}")

        print("\n3. Risk Metric Comparison (ES)")
        print(f"   ES Normal (mean):   ${df['es_normal'].mean():.2f}")
        print(f"   ES Quantile (mean): ${df['es_quantile'].mean():.2f}")

        print("\n4. Key Insights")

        # Count scenarios where quantile is more conservative
        more_conservative = (df["size_quantile_pct"] < df["size_normal_pct"]).sum()
        print(
            f"   Quantile more conservative: {more_conservative}/{n_scenarios} ({more_conservative / n_scenarios:.1%})"
        )

        # Fat tail handling
        fat_left = df[df["type"] == "fat_left"]
        if len(fat_left) > 0:
            avg_reduction = fat_left["size_diff_pct"].mean()
            print(f"   Avg size reduction in fat left tail: {avg_reduction:.2%}")

        print("\n" + "=" * 80)

        return df


def main():
    """Run backtest comparison"""

    comparison = BacktestComparison()
    df_results = comparison.run_comparison(n_scenarios=300)

    # Save results
    output_file = "backtest_quantile_vs_normal.csv"
    df_results.to_csv(output_file, index=False)
    print(f"\n✅ Results saved to: {output_file}")

    # Additional analysis
    print("\n" + "=" * 80)
    print("DETAILED BREAKDOWN")
    print("=" * 80)

    print("\nPosition Size Distribution:")
    print(df_results[["size_normal_pct", "size_quantile_pct"]].describe())

    print("\nCorrelation between methods:")
    corr = df_results["size_normal_pct"].corr(df_results["size_quantile_pct"])
    print(f"Correlation: {corr:.3f}")


if __name__ == "__main__":
    main()

"""
Unit tests for Treasury rate fetcher (FRED API integration).

Tests:
- API connection and rate fetching
- Fallback mechanism when API unavailable
- Caching behavior
- Multiple maturity support
"""

import pytest
from unittest.mock import patch, Mock
from app.lib.market.treasury import TreasuryRateFetcher, get_current_risk_free_rate


class TestTreasuryRateFetcher:
    """Test suite for FRED API Treasury rate fetching."""

    def test_fetch_with_valid_api_key(self):
        """Test fetching with valid FRED API key."""
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                # Mock successful API response
                mock_response = Mock()
                mock_response.json.return_value = {
                    "observations": [{"value": "4.16", "date": "2025-12-19"}]
                }
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response

                rate = TreasuryRateFetcher.fetch_current_rate("10Y")

                assert rate == pytest.approx(0.0416, rel=1e-4)
                assert mock_get.called

    def test_fetch_without_api_key(self):
        """Test fallback when no API key provided."""
        with patch("os.getenv", return_value=None):
            rate = TreasuryRateFetcher.fetch_current_rate("10Y", fallback_rate=0.0417)

            assert rate == 0.0417

    def test_fetch_with_missing_data(self):
        """Test fallback when API returns '.' (missing data)."""
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "observations": [{"value": ".", "date": "2025-12-19"}]
                }
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response

                rate = TreasuryRateFetcher.fetch_current_rate(
                    "10Y", fallback_rate=0.0417
                )

                assert rate == 0.0417

    def test_fetch_with_api_error(self):
        """Test fallback when API request fails."""
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get", side_effect=Exception("API Error")):
                rate = TreasuryRateFetcher.fetch_current_rate(
                    "10Y", fallback_rate=0.0417
                )

                assert rate == 0.0417

    def test_all_maturities(self):
        """Test that all supported maturities have series mappings."""
        for maturity in ["3M", "2Y", "10Y", "30Y"]:
            assert maturity in TreasuryRateFetcher.SERIES_MAP
            assert TreasuryRateFetcher.SERIES_MAP[maturity].startswith("DGS")

    def test_caching_behavior(self):
        """Test that daily caching works correctly."""
        from datetime import datetime

        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "observations": [{"value": "4.16", "date": "2025-12-19"}]
                }
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response

                # First call - should fetch
                rate1 = get_current_risk_free_rate("10Y")
                call_count_1 = mock_get.call_count

                # Second call - should use cache
                rate2 = get_current_risk_free_rate("10Y")
                call_count_2 = mock_get.call_count

                assert rate1 == rate2
                assert call_count_2 == call_count_1  # No additional API call

    def test_force_refresh(self):
        """Test force refresh bypasses cache."""
        with patch("os.getenv", return_value="test_api_key"):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "observations": [{"value": "4.16", "date": "2025-12-19"}]
                }
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response

                rate1 = get_current_risk_free_rate("10Y")
                call_count_1 = mock_get.call_count

                # Force refresh
                rate2 = get_current_risk_free_rate("10Y", force_refresh=True)
                call_count_2 = mock_get.call_count

                assert call_count_2 > call_count_1  # Additional API call made


class TestBrokerConfig:
    """Test suite for broker execution cost abstraction."""

    def test_alpaca_cost_calculation(self):
        """Test Alpaca execution cost calculation."""
        from app.lib.execution.broker_config import ALPACA_CONFIG

        # 100 shares @ $150
        cost = ALPACA_CONFIG.calculate_total_cost(100, 150.0)

        # Commission: max($0.005 * 100, $1) = $1
        # Spread: (5/10000) * $150 * 100 / 2 = $3.75
        # Total: $4.75
        expected = 1.0 + 3.75
        assert cost == pytest.approx(expected, rel=1e-2)

    def test_ibkr_lower_costs(self):
        """Test that IBKR has lower costs than Alpaca for liquid stocks."""
        from app.lib.execution.broker_config import ALPACA_CONFIG, IBKR_CONFIG

        shares, price = 100, 150.0

        alpaca_cost = ALPACA_CONFIG.calculate_total_cost(shares, price)
        ibkr_cost = IBKR_CONFIG.calculate_total_cost(shares, price)

        # IBKR should be cheaper (tighter spreads)
        assert ibkr_cost < alpaca_cost

    def test_get_broker_config(self):
        """Test broker config retrieval."""
        from app.lib.execution.broker_config import get_broker_config

        alpaca = get_broker_config("alpaca")
        assert alpaca.name == "alpaca"

        ibkr = get_broker_config("ibkr")
        assert ibkr.name == "ibkr"

        with pytest.raises(ValueError):
            get_broker_config("invalid_broker")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

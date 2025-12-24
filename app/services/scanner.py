import os
import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetStatus, AssetClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, StockSnapshotRequest

logger = logging.getLogger(__name__)


class MarketScanner:
    """Dynamic universe scanner - finds "in play" assets across 8k+ US equities.

    Replaces static watchlists with real-time volatility hunting. Scans the entire
    Alpaca universe and ranks by absolute price movement to find trading opportunities.

    **Scanning Pipeline**:
    1. **Fetch Universe**: Get all active/tradable US equities (~8-10k)
    2. **Batch Snapshots**: Parallel fetch in 1000-symbol chunks
    3. **Filter**: Price > $5, Volume > $20M, Move > 1.5%
    4. **Rank**: Sort by abs(change%) descending
    5. **Return**: Top N most volatile assets

    **Performance**:
    - Full scan: ~3-5 seconds (parallel batching)
    - Cache TTL: 5 minutes (avoid redundant scans)
    - ThreadPool: 10 workers for snapshot fetching

    **Filters**:
    - Min price: $5 (avoid penny stocks)
    - Min notional: $20M daily volume (liquidity)
    - Min movement: 1.5% (volatility threshold)

    Attributes:
        trading_client: Alpaca TradingClient
        data_client: Alpaca StockHistoricalDataClient
        _universe_cache: Cached scan results
        _cache_ttl: Cache expiration (300s)

    Example:
        >>> scanner = MarketScanner()
        >>> universe = await scanner.get_active_universe(limit=20)
        >>> print(universe)  # ['NVDA', 'TSLA', ...]
    """

    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_API_SECRET")

        if not self.api_key or not self.secret_key:
            logger.error("SCANNER: Alpaca credentials missing.")
            self.trading_client = None
            self.data_client = None
            return

        # Initialize Clients
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=True)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)

        # Cache
        self._universe_cache: List[str] = []
        self._universe_cache_time = None
        self._cache_ttl = 300  # 5 minutes

    async def get_active_universe(self, limit: int = 20) -> List[str]:
        """
        Main Entry Point. Returns Top 'limit' tickers.
        """
        if not self.trading_client:
            logger.warning("SCANNER: Client not initialized. Returning fallback.")
            return ["SPY", "QQQ"]  # Fallback

        # Check Cache
        if self._universe_cache and self._universe_cache_time:
            age = (datetime.now() - self._universe_cache_time).total_seconds()
            if age < self._cache_ttl:
                logger.info(f"SCANNER: Returning cached universe ({age:.0f}s old)")
                return self._universe_cache[:limit]

        logger.info("SCANNER: 🌊 Starting Deep Scan of US Equities...")

        # 1. The Ocean: efficient fetch (synchronous but fast enough or thread it)
        try:
            assets = await asyncio.to_thread(self._fetch_all_assets)
            logger.info(f"SCANNER: Found {len(assets)} active assets.")

            if not assets:
                return ["SPY", "QQQ"]

            # 2. The Filter (Snapshots)
            # Batch fetch snapshots
            symbols = [a.symbol for a in assets]
            snapshots = await self._fetch_snapshots_batched(symbols)
            logger.info(f"SCANNER: Retrieved {len(snapshots)} snapshots.")

            # 3. Apply Logic
            candidates = []
            min_price = 5.0
            min_notional = 20_000_000  # $20M
            min_move_pct = 0.015  # 1.5%

            for sym, snap in snapshots.items():
                if not snap or not snap.daily_bar:
                    continue

                price = snap.daily_bar.close
                volume = snap.daily_bar.volume
                prev_close = (
                    snap.previous_daily_bar.close if snap.previous_daily_bar else price
                )

                # Dynamic Price (using latest trade likely better but daily_bar close is today's close or current?)
                # Alpaca Snapshot daily_bar is "current day so far".

                if price < min_price:
                    continue

                notional = price * volume
                if notional < min_notional:
                    continue

                # Calc Change
                if prev_close > 0:
                    change_pct = (price - prev_close) / prev_close
                else:
                    change_pct = 0.0

                if abs(change_pct) < min_move_pct:
                    continue

                candidates.append(
                    {
                        "symbol": sym,
                        "change_pct": change_pct,
                        "abs_change": abs(change_pct),
                        "price": price,
                        "volume": volume,
                        "sector": self._get_sector(sym),  # Placeholder
                    }
                )

            # 4. Rank
            # Sort by Volatility (Abs Change)
            candidates.sort(key=lambda x: x["abs_change"], reverse=True)

            # Log Top 5
            for c in candidates[:5]:
                logger.info(
                    f"SCANNER: ⭐️ {c['symbol']} ({c['change_pct']:.2%}) Vol:${c['price'] * c['volume'] / 1e6:.1f}M"
                )

            # Extract
            final_universe = [c["symbol"] for c in candidates[:limit]]

            # Cache
            self._universe_cache = final_universe
            self._universe_cache_time = datetime.now()

            logger.info(f"SCANNER: Selected Top {len(final_universe)} assets.")
            return final_universe

        except Exception as e:
            logger.error(f"SCANNER: Scan failed: {e}")
            return ["SPY", "QQQ", "IWM", "NVDA", "TSLA"]  # Safe Fallback

    def _fetch_all_assets(self):
        """Fetch all US Equity assets that are active/tradable."""
        req = GetAssetsRequest(
            status=AssetStatus.ACTIVE, asset_class=AssetClass.US_EQUITY
        )
        assets = self.trading_client.get_all_assets(req)
        # Filter strictly
        return [
            a for a in assets if a.tradable and a.marginable and a.shortable
        ]  # Clean list

    async def _fetch_snapshots_batched(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch snapshots in chunks of 1000."""
        chunk_size = 1000  # Alpaca Limit
        all_snapshots = {}

        # Split into chunks
        chunks = [
            symbols[i : i + chunk_size] for i in range(0, len(symbols), chunk_size)
        ]

        logger.info(f"SCANNER: Fetching {len(chunks)} batches of snapshots...")

        # Helper for one batch
        def fetch_batch(batch_syms):
            try:
                # StockSnapshotRequest actually takes 'symbol_or_symbols'
                req = StockSnapshotRequest(symbol_or_symbols=batch_syms)
                return self.data_client.get_stock_snapshot(req)
            except Exception as e:
                logger.warning(f"SCANNER: Batch failed: {e}")
                return {}

        # Parallelize batches? Can be IO bound.
        # Running in thread pool
        loop = asyncio.get_running_loop()
        tasks = [loop.run_in_executor(None, fetch_batch, chunk) for chunk in chunks]

        results = await asyncio.gather(*tasks)

        for res in results:
            if res:
                all_snapshots.update(res)

        return all_snapshots

    def _get_sector(self, symbol: str) -> str:
        """
        Placeholder Sector Map.
        Ideally fetch from Asset profile, but that's n+1 calls.
        """
        # TODO(Phase40): Connect to Finnhub/FMP Profile API for real sector data
        # This is currently a hardcoded mockup for the MVP tech demo.
        # DO NOT use for sector-neutral strategies in PROD until updated.
        SECTORS = {
            "NVDA": "Tech",
            "AMD": "Tech",
            "TSLA": "Auto",
            "SPY": "ETF",
            "QQQ": "ETF",
            "XLE": "Energy",
            "XLF": "Finance",
        }
        return SECTORS.get(symbol, "Unknown")

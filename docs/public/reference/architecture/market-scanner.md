# Service Specification: Market Scanner

**Type:** Dynamic Universe Selector  
**Location:** `app/services/scanner.py`  
**Role:** Real-time discovery of "In Play" assets from the full US Equity universe

## 1. Architecture Overview

The `MarketScanner` scans **~8,000-10,000 US equities** every 5 minutes to identify the Top 20 most volatile and liquid assets. It replaces static watchlists with a dynamic, data-driven approach to universe selection.

### Core Design Principles

1. **Ocean to Drop**: Start with the entire tradable universe, filter aggressively
2. **Volatility First**: Rank by absolute price movement, not direction
3. **Liquidity Gate**: Enforce minimum notional volume to ensure executability
4. **Cache & Batch**: Minimize API calls through intelligent caching and batching

## 2. Class Architecture

### `MarketScanner`

```python
class MarketScanner:
    def __init__(self)
    async def get_active_universe(self, limit: int = 20) -> List[str]
    def _fetch_all_assets(self) -> List[Asset]
    async def _fetch_snapshots_batched(self, symbols: List[str]) -> Dict[str, Snapshot]
    def _get_sector(self, symbol: str) -> str
```

#### Initialization

**API Clients:**

- `TradingClient` (Alpaca) - Asset metadata
- `StockHistoricalDataClient` (Alpaca) - Snapshot data

**Internal State:**

- `_universe_cache`: List[str] - Cached Top 20 symbols
- `_universe_cache_time`: datetime - Cache timestamp
- `_cache_ttl`: 300 seconds (5 minutes)

**Fallback**: If credentials missing → `["SPY", "QQQ"]`

## 3. Execution Flow

### Step 1: Cache Check

```python
if cache_age < 300 seconds:
    return cached_universe[:limit]
```

**Cache Strategy:**

- TTL: 5 minutes (300 seconds)
- Invalidation: Age-based only (no event triggers)
- Rationale: Balance API costs vs freshness

### Step 2: Asset Discovery (`_fetch_all_assets`)

#### API Call

```python
GetAssetsRequest(
    status=AssetStatus.ACTIVE,
    asset_class=AssetClass.US_EQUITY
)
```

#### Filtering Logic

```python
assets = [
    a for a in all_assets 
    if a.tradable and a.marginable and a.shortable
]
```

**Requirements:**

- `status` = ACTIVE (not delisted/halted)
- `asset_class` = US_EQUITY (no crypto/forex)
- `tradable` = True
- `marginable` = True (can be traded on margin)
- `shortable` = True (can be shorted)

**Expected Output**: ~8,000-10,000 symbols

### Step 3: Snapshot Batching (`_fetch_snapshots_batched`)

**Challenge**: Alpaca API limit = 1,000 symbols per request

**Solution**: Chunk into batches of 1,000

```python
chunks = [
    symbols[i:i+1000] 
    for i in range(0, len(symbols), 1000)
]
```

**Parallel Execution:**

```python
loop = asyncio.get_running_loop()
tasks = [
    loop.run_in_executor(None, fetch_batch, chunk) 
    for chunk in chunks
]
results = await asyncio.gather(*tasks)
```

**Performance:**

- ~8 parallel requests for full universe
- Each request: ~500-800ms
- Total latency: <1 second (parallelized)

### Step 4: Filtering & Ranking

#### Filter Criteria

```python
min_price = 5.0           # Institutional quality
min_notional = 20_000_000 # $20M minimum liquidity
min_move_pct = 0.015      # 1.5% minimum volatility
```

**Filter Logic:**

```python
for sym, snap in snapshots.items():
    price = snap.daily_bar.close
    volume = snap.daily_bar.volume
    prev_close = snap.previous_daily_bar.close
    
    # Checks
    if price < min_price: continue
    if price * volume < min_notional: continue
    
    change_pct = (price - prev_close) / prev_close
    if abs(change_pct) < min_move_pct: continue
    
    candidates.append({
        "symbol": sym,
        "change_pct": change_pct,
        "abs_change": abs(change_pct),
        "price": price,
        "volume": volume,
        "sector": _get_sector(sym)
    })
```

#### Ranking Algorithm

```python
candidates.sort(key=lambda x: x["abs_change"], reverse=True)
```

**Sort Key**: Absolute price change (volatility, not direction)

**Rationale**: We want movement, not beta. A -5% drop is equally "in play" as a +5% rally.

### Step 5: Caching & Return

```python
final_universe = [c["symbol"] for c in candidates[:limit]]

self._universe_cache = final_universe
self._universe_cache_time = datetime.now()

return final_universe
```

## 4. Configuration Parameters

### Filter Thresholds

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `min_price` | $5.00 | Avoids penny stocks |
| `min_notional` | $20M | Ensures liquidity for $100k+ positions |
| `min_move_pct` | 1.5% | Filters out low-volatility assets |
| `limit` | 20 | Top N to track (configurable) |

### API Limits

| Limit | Value | Source |
|-------|-------|--------|
| Snapshot batch size | 1,000 | Alpaca API |
| Cache TTL | 300s | Internal |
| Timeout | 10s/request | Alpaca default |

## 5. Output Schema

### `get_active_universe` Returns

```python
List[str]  # Example: ["NVDA", "TSLA", "AMD", "SPY", ...]
```

**Sorted by**: Volatility (descending)

### Logging Output

```
SCANNER: 🌊 Starting Deep Scan of US Equities...
SCANNER: Found 8543 active assets.
SCANNER: Retrieved 8234 snapshots.
SCANNER: ⭐️ NVDA (4.23%) Vol:$1.2B
SCANNER: ⭐️ TSLA (-3.87%) Vol:$890M
SCANNER: ⭐️ AMD (3.45%) Vol:$760M
...
SCANNER: Selected Top 20 assets.
```

## 6. Fallback Strategies

### Failure Modes & Responses

| Failure | Fallback | Trigger |
|---------|----------|---------|
| API credentials missing | `["SPY", "QQQ"]` | Init |
| Snapshot fetch fails | `["SPY", "QQQ", "IWM", "NVDA", "TSLA"]` | Runtime exception |
| No candidates pass filter | `["SPY", "QQQ"]` | Empty candidates list |

**Philosophy**: Always return a valid universe (fail gracefully)

## 7. Sector Mapping (Placeholder)

```python
def _get_sector(self, symbol: str) -> str:
    SECTORS = {
        "NVDA": "Tech",
        "AMD": "Tech",
        "TSLA": "Auto",
        "SPY": "ETF",
        "QQQ": "ETF",
        "XLE": "Energy",
        "XLF": "Finance"
    }
    return SECTORS.get(symbol, "Unknown")
```

> [!NOTE]
> This is a **placeholder**. Ideally, fetch from Alpaca Asset API (`asset.sector`), but that requires N+1 calls. Future enhancement: Pre-cache sector map or use batch lookup.

## 8. Performance Characteristics

### Latency Breakdown

| Stage | Latency | Notes |
|-------|---------|-------|
| Asset fetch | ~200ms | Single API call |
| Snapshot batching | ~800ms | 8 parallel requests |
| Filtering | ~50ms | In-memory iteration |
| **Total (cold)** | **~1.1s** | First call |
| **Total (warm)** | **~0ms** | Cache hit |

### API Call Volume

- **Cold Start**: 1 (assets) + 8 (snapshot batches) = **9 calls**
- **Warm Cache**: **0 calls** (for 5 minutes)

## 9. Integration Points

### Inbound

- **Environment**: `ALPACA_API_KEY`, `ALPACA_API_SECRET`
- **Alpaca APIs**:
  - `TradingClient.get_all_assets()`
  - `StockHistoricalDataClient.get_stock_snapshot()`

### Outbound

- **Used by**: `IngestService` (dynamic subscription management)
- **Flow**: `Scanner.get_active_universe()` → `Ingest.update_subscriptions()`

## 10. Usage Examples

### Programmatic

```python
from app.services.scanner import MarketScanner

scanner = MarketScanner()
universe = await scanner.get_active_universe(limit=20)
print(universe)  # ["NVDA", "TSLA", ...]
```

### With Custom Limit

```python
top_10 = await scanner.get_active_universe(limit=10)
```

### Force Cache Bypass

```python
scanner._universe_cache_time = None  # Invalidate
universe = await scanner.get_active_universe()
```

## 11. Future Enhancements

### Planned Features

- [ ] **Sector Diversification**: Ensure Top 20 includes multiple sectors
- [ ] **Real Sector Mapping**: Fetch from Alpaca Asset API
- [ ] **Adaptive Thresholds**: Adjust `min_move_pct` based on VIX
- [ ] **Blacklist**: Exclude specific symbols (e.g., penny stocks that slip through)
- [ ] **Whitelist**: Force-include certain symbols (e.g., SPY always)

### Performance Optimizations

- [ ] **Delta Updates**: Only re-scan changed symbols (requires streaming)
- [ ] **PreMarket Scan**: Run at 9:00 AM to pre-warm cache
- [ ] **Historical Backfill**: Warm cache with yesterday's universe on startup

## 12. Validation & Monitoring

### Health Checks

```python
assert len(universe) > 0, "Empty universe (catastrophic failure)"
assert len(universe) <= limit, "Limit breach"
assert all(isinstance(s, str) for s in universe), "Invalid symbols"
```

### Metrics to Track

- **Universe Size** (daily average)
- **Symbol Churn** (% change from previous scan)
- **API Latency** (p50, p95, p99)
- **Cache Hit Rate** (%)

### Alerts

- 🚨 **CRITICAL**: Universe returns empty or fallback-only
- ⚠️ **WARNING**: API latency > 2s
- ℹ️ **INFO**: Cache miss rate > 50%

## 13. Appendix: Filter Justification

### Why $5 Minimum Price?

- **Liquidity**: Lower prices often = wider spreads
- **Volatility**: Penny stocks exhibit unnatural volatility
- **Institutional**: Most funds filter sub-$5 (Russell Index requirement)

### Why $20M Notional Volume?

- **Position Sizing**: Allows $100k position with <0.5% market impact
- **Execution**: Ensures tight spreads and fast fills
- **Risk**: Low-volume stocks = high slippage risk

### Why 1.5% Minimum Move?

- **Signal-to-Noise**: Smaller moves are often noise, not opportunity
- **Transaction Costs**: Need sufficient alpha to overcome costs
- **Regime Alignment**: Aligns with Physics Veto's tail event focus

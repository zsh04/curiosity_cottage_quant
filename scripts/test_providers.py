#!/usr/bin/env python3
"""
Test each market data provider individually to diagnose failures.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

sys.path.insert(0, os.path.abspath("."))

from app.adapters.tiingo import TiingoAdapter
from app.adapters.finnhub import FinnhubAdapter
from app.adapters.alphavantage import AlphaVantageAdapter
from app.adapters.twelvedata import TwelveDataAdapter
from app.adapters.marketstack import MarketStackAdapter
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest

# Test symbol
SYMBOL = "AAPL"

print(f"🔍 Testing Market Data Providers for {SYMBOL}\n")
print("=" * 70)

# 1. Alpaca
print("\n1️⃣  ALPACA")
try:
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_API_SECRET")
    if api_key and secret_key:
        client = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)
        req = StockLatestTradeRequest(symbol_or_symbols=SYMBOL)
        trade = client.get_stock_latest_trade(req)
        if SYMBOL in trade:
            price = float(trade[SYMBOL].price)
            print(f"   ✅ SUCCESS: ${price}")
        else:
            print(f"   ❌ FAIL: No data for {SYMBOL}")
    else:
        print("   ⚠️  SKIP: Credentials missing")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# 2. Tiingo
print("\n2️⃣  TIINGO")
try:
    tiingo = TiingoAdapter()
    price = tiingo.get_latest_price(SYMBOL)
    if price > 0:
        print(f"   ✅ SUCCESS: ${price}")
    else:
        print(f"   ❌ FAIL: Returned 0.0")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# 3. Finnhub
print("\n3️⃣  FINNHUB")
try:
    finnhub = FinnhubAdapter()
    quote = finnhub.get_quote(SYMBOL)
    if quote and quote.get("price"):
        print(f"   ✅ SUCCESS: ${quote['price']}")
    else:
        print(f"   ❌ FAIL: No data returned")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# 4. AlphaVantage
print("\n4️⃣  ALPHAVANTAGE")
try:
    av = AlphaVantageAdapter()
    quote = av.get_global_quote(SYMBOL)
    if quote and quote.get("price"):
        print(f"   ✅ SUCCESS: ${quote['price']}")
    else:
        print(f"   ❌ FAIL: No data returned")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# 5. TwelveData
print("\n5️⃣  TWELVEDATA")
try:
    twelve = TwelveDataAdapter()
    price = twelve.get_price(SYMBOL)
    if price > 0:
        print(f"   ✅ SUCCESS: ${price}")
    else:
        print(f"   ❌ FAIL: Returned 0.0")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# 6. MarketStack
print("\n6️⃣  MARKETSTACK")
try:
    ms = MarketStackAdapter()
    price = ms.get_latest_price(SYMBOL)
    if price > 0:
        print(f"   ✅ SUCCESS: ${price}")
    else:
        print(f"   ❌ FAIL: Returned 0.0")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# 7. yfinance (Fallback)
print("\n7️⃣  YFINANCE (Fallback)")
try:
    import yfinance as yf

    ticker = yf.Ticker(SYMBOL)
    info = ticker.info
    price = (
        info.get("regularMarketPrice")
        or info.get("currentPrice")
        or info.get("previousClose")
        or 0.0
    )
    if price > 0:
        print(f"   ✅ SUCCESS: ${price}")
    else:
        print(f"   ❌ FAIL: No data")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

print("\n" + "=" * 70)
print("✅ Provider Audit Complete")

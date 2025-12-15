import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from app.data.tiingo import TiingoProvider

# explicit load
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".env")


def verify_tiingo():
    print("--- Verifying Tiingo Provider ---")
    tiingo = TiingoProvider()

    # Check Price (Real-time/IEX)
    ticker = "AAPL"
    print(f"Fetching price for {ticker}...")
    try:
        price = tiingo.get_current_price(ticker)
        print(f"Current Price ({ticker}): {price}")
    except Exception as e:
        print(f"Price Error: {e}")

    # Check Bars (History)
    print(f"Fetching history for {ticker}...")
    try:
        df = tiingo.get_bars(ticker, limit=5)
        print("History Tail:")
        print(df)
    except Exception as e:
        print(f"History Error: {e}")

    # Check News
    print(f"Fetching news for {ticker}...")
    try:
        news = tiingo.get_news(ticker, limit=2)
        for n in news:
            print(f"- {n['headline']} ({n['source']})")
    except Exception as e:
        print(f"News Error: {e}")


if __name__ == "__main__":
    verify_tiingo()

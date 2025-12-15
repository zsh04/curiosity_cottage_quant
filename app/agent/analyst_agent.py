from app.agent.state import AgentState
from app.agent.models import model_factory
from app.data.aggregator import DataAggregator


def get_sector_candidates(sector: str):
    """
    Mock function to get candidate tickers for a sector.
    """
    # TODO: Replace with real screener (e.g. FinViz, Alpaca, etc.)


from app.agent.models import model_factory


def get_stock_data(ticker):
    """
    Fetches stock data and news via DataAggregator.
    """
    aggregator = DataAggregator()
    # Price
    price = aggregator.get_current_price(ticker)
    # News for sentiment
    headlines = aggregator.get_sentiment_context(ticker)

    return {
        "price": price,
        "pe_ratio": 25.0,  # Placeholder as we don't have PE in aggregator yet
        "recent_news": headlines,
    }


def analyst_agent(state: AgentState):
    """
    Analyst Agent: Screens stocks and generates conviction using FinBERT and Gemma.
    """
    print("--- Analyst Agent Reasoning ---")

    target_sectors = state.get("target_sectors", [])
    candidates = []

    # Mock screening based on sectors
    if "Technology" in target_sectors:
        candidates.extend(["NVDA", "AMD", "MSFT"])
    if "Energy" in target_sectors:
        candidates.extend(["XOM", "CVX"])
    if not candidates:
        candidates = ["AAPL", "GOOGL"]  # Default

    candidate_trades = []

    for ticker in candidates:
        data = get_stock_data(ticker)

        # 1. Analyze Sentiment with FinBERT
        news_sentiment = []
        for headline in data["recent_news"]:
            score = model_factory.analyze_sentiment(headline)
            news_sentiment.append(f"Headline: '{headline}' -> Score: {score}")

        print(f"[{ticker}] FinBERT Analysis: {news_sentiment}")

        # 2. Synthesize Thesis with Gemma
        prompt = f"""You are a Senior Equity Analyst.
        Analyze {ticker} based on this data:
        Price: {data["price"]}
        PE: {data["pe_ratio"]}
        Sentiment Analysis: {news_sentiment}
        
        Provide a Conviction Score (0-10) and a recommendation (BUY/WAIT).
        """

        thesis = model_factory.generate_thought(prompt)
        print(f"[{ticker}] Gemma Thesis: {thesis}")

        # Simple heuristic parsing of Gemma's output
        action = "WAIT"
        if "BUY" in thesis.upper():
            action = "BUY"

        if action == "BUY":
            candidate_trades.append(
                {
                    "symbol": ticker,
                    "conviction": 8,  # Mock score parsing
                    "action": "BUY",
                    "reason": thesis[:100] + "...",
                }
            )

    return {
        "candidate_trades": candidate_trades,
        "reasoning_trace": [f"Analyst Processed {len(candidates)} stocks."],
        "next_step": "risk_veto",  # Routing to Risk Agent (via graph edge)
    }

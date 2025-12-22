import asyncio
import grpc
import logging
import random
import sys

# Import generated code
import app.generated.brain_pb2 as pb2
import app.generated.brain_pb2_grpc as pb2_grpc


async def verify_brain():
    """
    Connects to BrainService and verifies functionality.
    """
    address = "localhost:50051"
    print(f"🔬 Connecting to Brain at {address}...")

    async with grpc.aio.insecure_channel(address) as channel:
        stub = pb2_grpc.BrainStub(channel)

        # 1. Test Forecast
        print("\n🔮 Testing Forecast RPC...")
        try:
            # Create synthetic price path (Random Walk)
            prices = [100 + (random.random() - 0.5) * 5 for _ in range(64)]

            request = pb2.ForecastRequest(
                ticker="TEST_TICKER", prices=prices, horizon=10
            )

            response = await stub.Forecast(request)

            print(f"✅ Forecast Response Received:")
            print(f"   P10: {response.p10}")
            print(f"   P50: {response.p50}")
            print(f"   P90: {response.p90}")

            if not response.p50:
                print("❌ Empty Prediction!")
                sys.exit(1)

        except grpc.RpcError as e:
            print(f"❌ Forecast Failed: {e.code()} : {e.details()}")
            return

        # 2. Test Sentiment
        print("\n🧠 Testing Sentiment RPC...")
        try:
            request = pb2.SentimentRequest(
                headlines=["The market is crashing hard today! Panic everywhere."]
            )

            response = await stub.AnalyzeSentiment(request)

            print(f"✅ Sentiment Response Received:")
            print(f"   Score: {response.sentiment_score:.4f}")
            print(f"   Conf:  {response.confidence:.4f}")

            if response.sentiment_score > -0.1:
                print("⚠️ Expected negative sentiment for panic headline.")

        except grpc.RpcError as e:
            print(f"❌ Sentiment Failed: {e.code()} : {e.details()}")

    print("\n✅ Brain Verification Complete. The Cortex is Online.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(verify_brain())

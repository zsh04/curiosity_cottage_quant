import logging
import asyncio
import grpc

# Generated Protobufs
import app.generated.brain_pb2 as pb2
import app.generated.brain_pb2_grpc as pb2_grpc

# Internal services
from app.services.forecast import TimeSeriesForecaster
from app.adapters.sentiment import SentimentAdapter

import torch

logger = logging.getLogger(__name__)


class BrainService(pb2_grpc.BrainServicer):
    """gRPC microservice hosting Chronos forecasting and FinBERT sentiment models.

    Provides high-performance AI inference via gRPC, separating model execution
    from the main agent loop for better resource isolation and scalability.

    **Services Provided**:
    1. **Forecast (Chronos)**: Time series probabilistic forecasting
    2. **AnalyzeSentiment (FinBERT)**: News headline sentiment analysis

    **Architecture**:
    - gRPC server on port 50051
    - Async service methods (asyncio)
    - Protobuf serialization for efficiency
    - Model initialization at startup

    **Models**:
    - TimeSeriesForecaster: Chronos-bolt ensemble forecasting
    - SentimentAdapter: FinBERT ONNX runtime

    Attributes:
        forecaster: TimeSeriesForecaster instance
        sentiment: SentimentAdapter instance

    Example:
        >>> # Start server
        >>> asyncio.run(serve())  # Listens on [::]:50051

        >>> # Client usage (from Boyd)
        >>> stub.Forecast(ForecastRequest(prices=[...]))
    """

    def __init__(self):
        # Verify PB2 Definition at runtime
        try:
            test = pb2.ForecastResponse(signal="TEST")
            logger.info("✅ PB2 Signal Field Verified via Instantiation.")
        except Exception as e:
            logger.critical(f"❌ PB2 Signal Field MISSING: {e}")
            # We don't raise here to allow startup, but log critical failure.

        logger.info("🧠 BrainService: Initializing Neural Core...")

        # Initialize Models
        self.forecaster = TimeSeriesForecaster()
        self.sentiment = SentimentAdapter()

        logger.info("🧠 BrainService: Ready.")

    async def Forecast(
        self, request: pb2.ForecastRequest, context: grpc.aio.ServicerContext
    ) -> pb2.ForecastResponse:
        """
        Chronos Inference via gRPC.
        """
        try:
            # prices = list(request.prices) (Historical Context)
            prices = list(request.prices)

            # Convert to Tensor for Forecaster
            context_tensor = torch.tensor(prices, dtype=torch.float32)

            # Call Async Forecaster (The Oracle)
            result = await self.forecaster.predict_ensemble(
                context_tensor=context_tensor, current_prices=prices
            )

            # Extract Core Components (FLAT structure from _fuse_signals)
            chronos_data = result.get("chronos", {})
            raf_data = result.get("raf", {})
            meta_data = result.get("meta", {})

            # Use `orjson` for high-speed serialization if possible, else json
            import json

            try:
                import orjson

                def dumps(x):
                    return orjson.dumps(
                        x, option=orjson.OPT_SERIALIZE_NUMPY, default=str
                    ).decode()
            except ImportError:
                dumps = lambda x: json.dumps(x, default=str)

            q_list = chronos_data.get("quantiles", [])
            logger.debug(f"📊 BrainService: Quantiles extracted: {len(q_list)} values")
            logger.debug(f"📊 chronos_data keys: {list(chronos_data.keys())}")
            if q_list:
                logger.debug(f"📊 First 3 quantiles: {q_list[:3]}")

            return pb2.ForecastResponse(
                # Decision
                signal=result.get("signal", "NEUTRAL"),
                confidence=result.get("confidence", 0.0),
                reasoning=result.get("reasoning", "No context."),
                # Metrics (From Chronos)
                p10=chronos_data.get("p10", 0.0),
                p50=chronos_data.get("p50", 0.0),
                p90=chronos_data.get("p90", 0.0),
                trend=chronos_data.get("trend", 0.0),
                # Full Context (Serialized)
                chronos_json=dumps(result.get("chronos", chronos_data)),
                raf_json=dumps(result.get("raf", raf_data)),
                meta_json=dumps(meta_data),
                full_quantiles=q_list,
            )

        except Exception as e:
            logger.error(f"BrainService.Forecast Error: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def AnalyzeSentiment(
        self, request: pb2.SentimentRequest, context: grpc.aio.ServicerContext
    ) -> pb2.SentimentResponse:
        """
        FinBERT Inference via gRPC.
        """
        try:
            headlines = request.headlines
            if not headlines:
                return pb2.SentimentResponse(sentiment_score=0.0, confidence=0.0)

            # Analyze first headline for now (MVP)
            # Or average them?
            text = headlines[0]

            # SentimentAdapter is sync, so run in executor?
            # Actually SentimentAdapter is standard sync.
            # Since ONNX might release GIL, direct call might be okay, but safer in executor.

            # But `SentimentAdapter` call is fast (<50ms).
            result = self.sentiment.analyze(text)

            # Result: {"label": "positive", "score": 0.9}
            # We need to map to scalar score (-1 to 1).
            label = result.get("label", "neutral").lower()
            conf = result.get("score", 0.0)

            score_map = {
                "positive": 1.0,
                "bullish": 1.0,
                "neutral": 0.0,
                "negative": -1.0,
                "bearish": -1.0,
            }

            sentiment_scalar = score_map.get(label, 0.0) * conf

            return pb2.SentimentResponse(
                sentiment_score=sentiment_scalar, confidence=conf
            )

        except Exception as e:
            logger.error(f"BrainService.AnalyzeSentiment Error: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))


async def serve():
    address = "[::]:50051"
    server = grpc.aio.server()
    pb2_grpc.add_BrainServicer_to_server(BrainService(), server)
    server.add_insecure_port(address)

    logger.info(f"🧠 Brain Server starting on {address}")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())

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
    """
    The Brain gRPC Service.
    Hosts the AI models (Chronos/FinBERT) as a high-performance microservice.
    """

    def __init__(self):
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
            # ticker = request.ticker (Unused in MVP)
            prices = list(request.prices)
            # horizon = request.horizon (Unused in MVP - fixed by config)

            # Convert to Tensor for Forecaster
            # Context tensor shape: (Time,)
            # Forecaster handles device placement
            context_tensor = torch.tensor(prices, dtype=torch.float32)

            # Call Async Forecaster
            # Note: predict_ensemble expects context_tensor and raw list
            # We use `prices` as raw list.

            # Since this is a gRPC call, we likely want just the "Chronos" part or the fused part?
            # The proto returns p10, p50, p90.
            # `predict_ensemble` provides detailed dict.
            # Let's use `predict_ensemble` to get the full power (Fusion/RAF).

            result = await self.forecaster.predict_ensemble(
                context_tensor=context_tensor, current_prices=prices
            )

            # Extract quantiles from the result components or the ensemble
            # The `predict_ensemble` output structure is flat:
            # "components": {"chronos": {p10, p50...}, ...}

            chronos_data = result.get("components", {}).get("chronos", {})

            # Note: The proto expects REPEATED doubles for p10/p50/p90
            # But `predict_ensemble` -> `_run_chronos_batch` currently returns SINGLE floats (terminal values).
            # We might want the FULL CURVE.
            # Let's check `_run_chronos_batch`. It returns:
            # "p10": float(p10), "p50": float... which are TERMINAL values.
            #
            # Ideally Forecast RPC returns the path.
            # But for now, complying with current implementation of `predict_ensemble`:
            # We will return list of [val] (length 1) or extrapolate?
            #
            # Let's LOOK at the proto. `repeated double p50`.
            # If we only have terminal value, we return [value].
            #
            # TODO: Upgrade `TimeSeriesForecaster` to return full curve if needed.
            # For now, we wrap the terminal value in a list.

            return pb2.ForecastResponse(
                p10=[chronos_data.get("p10", 0.0)],
                p50=[chronos_data.get("p50", 0.0)],
                p90=[chronos_data.get("p90", 0.0)],
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

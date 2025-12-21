import os
import sys
import logging
import time

# Add project root
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Setup Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | VERIFY | %(levelname)s | %(message)s"
)
logger = logging.getLogger("verify_neural")


def verify_sentiment():
    logger.info("--- Testing Sentiment Engine (ONNX) ---")
    try:
        from app.adapters.sentiment import SentimentAdapter

        s = SentimentAdapter()
        if s.pipe:
            start = time.time()
            result = s.analyze("The market is crashing hard today.")
            dur = (time.time() - start) * 1000
            logger.info(f"Sentiment Analysis: {result} | Time: {dur:.2f}ms")

            # Check if it's using the right backend (heuristic)
            # Optimum pipeline wrapper usually has 'model' attribute being ORTModel...
            if hasattr(s.pipe, "model"):
                model_type = type(s.pipe.model).__name__
                logger.info(f"Model Type: {model_type}")
                if "ORT" in model_type:
                    logger.info("✅ ONNX Runtime Confirmed via Class Name")
                else:
                    logger.warning(
                        f"⚠️ Model type {model_type} does not explicitly look like ORT."
                    )
        else:
            logger.error("❌ Sentiment Pipe failed to init")
    except Exception as e:
        logger.error(f"❌ Sentiment Verification Failed: {e}")


def verify_forecast():
    logger.info("--- Testing Forecast Engine (Chronos-Bolt/MPS) ---")
    try:
        from app.services.chronos import ChronosService

        # Force model name check
        c = ChronosService()
        if c.pipeline:
            # Check device
            logger.info(f"Chronos Device: {c.device}")
            if c.device == "mps":
                logger.info("✅ MPS Acceleration Active")
            else:
                logger.warning("⚠️ Running on CPU (Expected MPS on Apple Silicon)")

            # Check model name in pipeline logic if possible, or just trust logs
            # Run inference
            c.update_buffer(100.0)
            for i in range(50):
                c.update_buffer(100.0 + i)

            start = time.time()
            # We need to hack the throttle to force run
            c.tick_counter = 9  # next is 10
            forecast = c.forecast()
            dur = (time.time() - start) * 1000

            if forecast:
                logger.info(f"Forecast Generated: {forecast.p50} | Time: {dur:.2f}ms")
            else:
                logger.warning("⚠️ No forecast returned (Context length issue?)")

        else:
            logger.error(
                "❌ Chronos Pipeline failed to init (Check logs for Library missing)"
            )

    except Exception as e:
        logger.error(f"❌ Forecast Verification Failed: {e}")


if __name__ == "__main__":
    verify_sentiment()
    verify_forecast()

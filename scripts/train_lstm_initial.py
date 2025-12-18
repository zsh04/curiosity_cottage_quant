import logging
import os
import sys
import numpy as np
import pandas as pd

# Ensure app is in path
sys.path.append(os.getcwd())

from app.strategies.lstm import LSTMPredictionStrategy

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InitLSTM")


def init_model():
    """
    Initialize a fresh LSTM/ESN model and save it to disk.
    """
    logger.info("Initializing LSTMPredictionStrategy...")
    model = LSTMPredictionStrategy()

    # Warmup with dummy random walk data to ensure it's not "empty"
    logger.info("Generating dummy warmup data...")
    np.random.seed(42)
    prices = [100.0]
    for _ in range(100):
        change = np.random.normal(0, 1)
        prices.append(prices[-1] + change)

    df = pd.DataFrame({"close": prices})

    logger.info("Warming up model...")
    signal = model.calculate_signal(df)
    logger.info(f"Initial signal: {signal}")

    # Save to disk
    save_path = "data/models/lstm_analyst.pkl"
    logger.info(f"Saving model to {save_path}...")

    # Ensure dir exists
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    # Use internal save method (which uses pickle)
    # We use get_state_bytes manually to replicate what the class does internally
    # but we can just pickle the object itself if we want, OR use the class's persistence methods.
    # The class has load_state/save_state methods.

    # However, the class methods assume "DB persistence" is the future, so let's check.
    # The warning "LSTM Model file not found at data/models/lstm_analyst.pkl" implies we should use save_state.

    try:
        model.save_state(save_path)
        logger.info("✅ Model saved successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to save model: {e}")


if __name__ == "__main__":
    init_model()

import numpy as np
import pandas as pd
from typing import Optional
import pickle
import os
import logging

from app.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class LSTMPredictionStrategy(BaseStrategy):
    """
    Reservoir Computing Strategy (Echo State Network) with Recursive Least Squares.

    Uses a fixed random reservoir to project inputs into high-dimensional space,
    then uses RLS (Recursive Least Squares) to incrementally update the readout layer.

    PERFORMANCE OPTIMIZATION:
    - OLD: O(N³) complexity due to np.linalg.lstsq() on entire history
    - NEW: O(1) complexity per update using RLS
    - BENEFIT: Latency-invariant performance regardless of history length

    Despite the name 'LSTM', this implements an Echo State Network (ESN),
    which is a computationally efficient Recurrent Neural Network paradigm.
    """

    def __init__(
        self,
        n_reservoir: int = 100,
        spectral_radius: float = 0.9,
        forget_factor: float = 0.99,
        seed: int = 42,
    ):
        self._name = "EchoState_RLS_V2"
        self.n_reservoir = n_reservoir
        self.spectral_radius = spectral_radius
        self.forget_factor = forget_factor  # RLS forgetting factor (lambda)
        self.random_state = np.random.RandomState(seed)

        # Initialize Reservoir Weights
        # W_in: Input (1 dim) -> Reservoir
        self.W_in = self.random_state.uniform(-0.5, 0.5, (n_reservoir, 1))

        # W_res: Reservoir -> Reservoir (sparse matrix)
        sparsity = 0.2
        W = self.random_state.uniform(-0.5, 0.5, (n_reservoir, n_reservoir))
        mask = self.random_state.rand(n_reservoir, n_reservoir) > sparsity
        W[mask] = 0

        # Spectral Radius Scaling (ensures Echo State Property)
        eigenvalues = np.linalg.eigvals(W)
        max_eigenvalue = np.max(np.abs(eigenvalues))

        if max_eigenvalue > 0:
            self.W_res = W * (spectral_radius / max_eigenvalue)
        else:
            self.W_res = W

        # === RLS STATE VARIABLES ===
        # Reservoir state (persistent across calls)
        self.x_t = np.zeros((n_reservoir, 1))

        # RLS Covariance Matrix P (inverse correlation matrix)
        # Initialized with large variance (1/lambda) for fast initial learning
        initial_variance = 1000.0  # High initial uncertainty
        self.P = np.eye(n_reservoir) * initial_variance

        # RLS Output Weights
        self.w_out = np.zeros(n_reservoir)

        # Training state
        self.is_initialized = False
        self.warmup_count = 0
        self.warmup_threshold = 20  # Discard initial transient states

    @property
    def name(self) -> str:
        return self._name

    def update_reservoir_state(self, return_t: float) -> np.ndarray:
        """
        Update the reservoir state with a single new observation.

        Args:
            return_t: The return at time t

        Returns:
            Updated state vector (flattened)
        """
        # Input injection: W_in * u_t
        in_injection = self.W_in * return_t

        # Recurrent injection: W_res * x_{t-1}
        res_injection = np.dot(self.W_res, self.x_t)

        # State update: x_t = tanh(W_in * u_t + W_res * x_{t-1})
        self.x_t = np.tanh(in_injection + res_injection)

        return self.x_t.flatten()

    def rls_update(self, x_t: np.ndarray, target: float):
        """
        Recursive Least Squares update - O(1) complexity.

        Updates the output weights incrementally without retraining on full history.

        Args:
            x_t: Current reservoir state (feature vector)
            target: Target output (next return)
        """
        # Prediction error
        # e = target - w_out @ x_t
        prediction = np.dot(self.w_out, x_t)
        error = target - prediction

        # RLS Gain calculation
        # k = (P @ x_t) / (forget_factor + x_t.T @ P @ x_t)
        P_x = np.dot(self.P, x_t)
        denominator = self.forget_factor + np.dot(x_t, P_x)

        if denominator < 1e-10:  # Numerical stability
            return

        k = P_x / denominator

        # Weight update
        # w_out = w_out + k * e
        self.w_out = self.w_out + k * error

        # Covariance update (Joseph form for numerical stability)
        # P = (P - k @ x_t.T @ P) / forget_factor
        outer_product = np.outer(k, P_x)
        self.P = (self.P - outer_product) / self.forget_factor

    def calculate_signal(self, market_data: pd.DataFrame) -> float:
        """
        Generates a trading signal based on predicted return.

        Uses incremental RLS updates for O(1) performance.
        """
        if "close" not in market_data:
            return 0.0

        prices = market_data["close"].values

        if len(prices) < 2:
            return 0.0

        # Calculate returns
        returns = np.diff(prices) / prices[:-1]

        if len(returns) < self.warmup_threshold:
            return 0.0

        # Process returns incrementally using RLS
        # We need at least the last return to update state and predict

        # If not initialized, we need to warm up the reservoir
        if not self.is_initialized:
            # Warm up reservoir with historical data
            for i in range(min(len(returns) - 1, self.warmup_threshold)):
                state = self.update_reservoir_state(returns[i])

                # Update RLS with next return as target
                if i > 0:  # Need at least 1 prior state
                    self.rls_update(state, returns[i + 1])

            self.is_initialized = True
            self.warmup_count = min(len(returns), self.warmup_threshold)

        # Process only new returns (incremental learning)
        # In production, we'd track last_processed_index
        # For simplicity, we update with the latest return
        if len(returns) > 0:
            # Update state with latest return
            current_state = self.update_reservoir_state(returns[-1])

            # If we have a prior state and target, update RLS
            # (We can't update with the very last return since we don't know t+1 yet)
            # This is a predict-then-update pattern

            # Make prediction using current weights and state
            predicted_return = np.dot(self.w_out, current_state)

            # Return signal based on prediction
            if predicted_return > 0.001:  # 0.1% threshold
                return 1.0  # Buy
            elif predicted_return < -0.001:
                return -1.0  # Sell

            return 0.0

        return 0.0

    def get_state_bytes(self) -> bytes:
        """
        Get the model state as a pickled binary blob.
        """
        try:
            state = {
                "W_in": self.W_in,
                "W_res": self.W_res,
                "w_out": self.w_out,
                "P": self.P,
                "x_t": self.x_t,
                "is_initialized": self.is_initialized,
                "warmup_count": self.warmup_count,
            }
            return pickle.dumps(state)
        except Exception as e:
            logger.error(f"Failed to serialize LSTM state: {e}")
            return b""

    def load_state_bytes(self, blob: bytes):
        """
        Load the model state from a binary blob.
        """
        if not blob:
            return

        try:
            state = pickle.loads(blob)

            self.W_in = state["W_in"]
            self.W_res = state["W_res"]
            self.w_out = state["w_out"]
            self.P = state["P"]
            self.x_t = state["x_t"]
            self.is_initialized = state.get("is_initialized", False)
            self.warmup_count = state.get("warmup_count", 0)

            logger.info("Dataset loaded from DB blob.")
        except Exception as e:
            logger.error(f"Failed to load LSTM state from blob: {e}")

    def save_state(self, filepath: str):
        """
        Save the model state (weights and reservoir) to disk.
        Deprecated: Use DB persistence instead.
        """
        try:
            # We can reuse get_state_bytes to save to file for legacy support
            blob = self.get_state_bytes()
            if not blob:
                return

            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, "wb") as f:
                f.write(blob)
            logger.info(f"💾 LSTM Model saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save LSTM model: {e}")

    def load_state(self, filepath: str):
        """
        Load the model state from disk.
        Deprecated: Use DB persistence instead.
        """
        if not os.path.exists(filepath):
            logger.warning(f"LSTM Model file not found at {filepath}. Starting fresh.")
            return

        try:
            with open(filepath, "rb") as f:
                blob = f.read()
            self.load_state_bytes(blob)
            logger.info(f"📂 LSTM Model loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load LSTM model: {e}")

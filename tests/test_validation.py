import unittest
import pandas as pd
import numpy as np
from app.lib.validation import PurgedKFold


class TestPurgedKFold(unittest.TestCase):
    def setUp(self):
        # Create a sample time series DataFrame
        self.dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        self.X = pd.DataFrame({"price": np.random.randn(100)}, index=self.dates)

        # Create a 'y' DataFrame with 't1' (outcome timestamp)
        # Assume label outcome is t + 5 days
        self.t1 = self.dates + pd.Timedelta(days=5)
        self.y = pd.DataFrame({"t1": self.t1}, index=self.dates)

    def test_embargo(self):
        """Test that embargo drops samples immediately after test set."""
        # 1% embargo of 100 samples = 1 sample
        kf = PurgedKFold(n_splits=5, pct_embargo=0.01)

        for train_indices, test_indices in kf.split(self.X, self.y):
            max_test_idx = test_indices.max()

            # Find train indices that come after test set
            train_after = train_indices[train_indices > max_test_idx]

            if len(train_after) > 0:
                # The first index of the subsequent training block should be
                # at least max_test_idx + 1 + embargo (1) = max_test_idx + 2
                min_train_after = train_after.min()
                expected_min = max_test_idx + 1 + 1  # +1 for next index, +1 for embargo

                # Note: indices are 0-based.
                # If test is [0..19], next is 20. Embargo=1 means drop 20. Start at 21.

                self.assertGreaterEqual(min_train_after, expected_min)

    def test_purging(self):
        """Test that training samples overlapping with test set are purged."""
        kf = PurgedKFold(n_splits=5, pct_embargo=0.0)  # No embargo to isolate purging

        for train_indices, test_indices in kf.split(self.X, self.y):
            test_start = self.X.index[test_indices.min()]
            test_end = self.X.index[test_indices.max()]

            # Check every training sample
            for tr_idx in train_indices:
                tr_outcome = self.y.iloc[tr_idx]["t1"]
                tr_start = self.X.index[tr_idx]

                # Condition for overlap:
                # Train outcome > Test start AND Train start < Test end

                # Assert NO overlap
                is_overlap = (tr_outcome > test_start) and (tr_start < test_end)
                self.assertFalse(
                    is_overlap,
                    f"Training sample at {tr_start} with outcome {tr_outcome} overlaps with test [{test_start}, {test_end}]",
                )


if __name__ == "__main__":
    unittest.main()

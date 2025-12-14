import numpy as np
import pandas as pd
from sklearn.model_selection import KFold


class PurgedKFold(KFold):
    """
    K-Fold Cross-Validation with Purging and Embargoing for financial time-series.

    Ref: Advances in Financial Machine Learning, Chapter 7
    """

    def __init__(self, n_splits: int = 5, pct_embargo: float = 0.01, **kwargs):
        """
        Args:
            n_splits: Number of folds.
            pct_embargo: Percent of total samples to drop after the test set
                         to prevent leakage from the test set into the training set.
        """
        super().__init__(n_splits=n_splits, shuffle=False, **kwargs)
        self.pct_embargo = pct_embargo

    def split(self, X: pd.DataFrame, y=None, groups=None):
        """
        Generate indices to split data into training and test set.

        Args:
            X: Dataframe containing time-series data. Index must be time-sorted.
            y: Target variable (pandas Series). Must contain 't1' (event end time)
               if purging is required based on event overlap.
               If y is just a target series without 't1', only embargoing is applied.
        """
        indices = np.arange(X.shape[0])
        n_embargo = int(X.shape[0] * self.pct_embargo)

        for train_indices, test_indices in super().split(X, y, groups):
            # --- Embargoing ---
            # Embargo is applied to training samples that strictly follow the test set.
            # In standard KFold without shuffle, the test set moves across the timeline.
            # When test set is in the middle, we must embargo the *start* of the
            # training block that comes immediately *after* the test set.

            max_test_idx = test_indices.max()

            # Find train indices that come after the test set
            train_after_test = train_indices[train_indices > max_test_idx]

            if len(train_after_test) > 0:
                # The embargo cutoff is the first index of the training set after test + n_embargo
                # Basically, we drop the first n_embargo indices from this block
                cutoff_idx = max_test_idx + n_embargo

                # Filter out training indices that are within the embargo zone
                train_indices = train_indices[train_indices > cutoff_idx]

            # --- Purging ---
            # If an events Series with 't1' (end times) is passed, purge overlaps.
            # This logic assumes 'y' (or X) has info about event duration.
            # For simplicity here, we assume if y is a DataFrame with 't1', we use it.
            # Otherwise if we just have raw bars, standard embargo might be enough if
            # goals are simpler, but the requirement is "Purged & Embargoed".

            # Implementation assuming y contains 't1' (timestamp when the label is determined)
            if hasattr(y, "columns") and "t1" in y.columns:
                t1 = y["t1"]
                test_start_time = X.index[test_indices.min()]
                test_end_time = X.index[test_indices.max()]

                # t1 associated with training samples
                train_t1 = t1.iloc[train_indices]

                # Purge training samples where the outcome (t1) overlaps with test window
                # Overlap condition:
                # A training label outcome occurs AFTER test start AND training sample starts BEFORE test end
                # (Standard overlap logic)

                # However, a simpler, stricter purge for standard KFold (contiguous blocks):
                # Just ensure no training sample's label *overlaps* in time with the test data's *observation*
                # range OR test spread.

                # Let's purge based on index overlap with t1.
                # Train samples must not have their `t1` fall into the test dataset's time range.
                # AND Train samples (their index time) must not fall into Test's t1 range (if test labels were generated).

                # Simplified Purging for this step:
                # Remove train indices i where:
                # t1[i] >= test_start_index_time  AND  index[i] <= test_end_index_time

                train_indices_to_keep = []
                for train_i in train_indices:
                    tr_req_end = t1.iloc[train_i]
                    tr_req_start = X.index[train_i]

                    # Check overlap with Test block [min_test_time, max_test_t1]
                    # Note: We need max_test_t1.

                    # For standard blocking, usually test set is a contiguous chunk of bars.
                    # We just need to make sure a training sample's outcome doesn't use data from the test period.

                    if tr_req_end > test_start_time and tr_req_start < test_end_time:
                        continue  # Drop it
                    train_indices_to_keep.append(train_i)

                train_indices = np.array(train_indices_to_keep)

            yield train_indices, test_indices

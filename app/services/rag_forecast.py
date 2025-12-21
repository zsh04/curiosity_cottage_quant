"""
Retrieval Augmented Forecasting (RAF) Service.

Uses LanceDB to store and retrieve market state embeddings (time-series windows)
to find historical analogs for the current market conditions.

Identity: The Librarian
"""

import lancedb
import pyarrow as pa
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.config import settings
import logging

# Configure Logger
logger = logging.getLogger("MarketMemory")
logging.basicConfig(level=logging.INFO)


class MarketMemory:
    """
    Vector Database for Market Patterns using LanceDB.
    """

    def __init__(self, uri: str = settings.LANCEDB_URI):
        self.uri = uri
        self.db = lancedb.connect(uri)
        self.table_name = "market_patterns"
        self._init_table()

    def _init_table(self):
        """Initialize the LanceDB table with the correct schema if it doesn't exist."""
        schema = pa.schema(
            [
                pa.field("vector", pa.list_(pa.float32(), 64)),  # 64-minute window
                pa.field("symbol", pa.string()),
                pa.field("timestamp", pa.timestamp("us")),
                pa.field("outcome", pa.float32()),  # 15-min forward return
            ]
        )

        if self.table_name not in self.db.table_names():
            logger.info(f"Creating new LanceDB table: {self.table_name}")
            self.tbl = self.db.create_table(self.table_name, schema=schema)
        else:
            self.tbl = self.db.open_table(self.table_name)

    def search_analogs(
        self,
        current_vector: List[float],
        top_k: int = settings.RAF_TOP_K,
        cutoff_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Search for historical analogs to the current market vector.

        Args:
            current_vector: Normalized 64-minute price series (list of floats).
            top_k: Number of neighbors to retrieve.
            cutoff_timestamp: If set, restricts search to patterns before this time (Strict Causality).

        Returns:
            Dict containing:
            - weighted_outcome: Weighted average of future returns from analogs.
            - confidence: Similarity score (1 - distance).
            - matches: List of match details.
        """
        if len(current_vector) != settings.RAF_WINDOW_SIZE:
            logger.warning(
                f"Vector size mismatch. Expected {settings.RAF_WINDOW_SIZE}, got {len(current_vector)}"
            )
            return {"weighted_outcome": 0.0, "confidence": 0.0, "matches": []}

        # LanceDB Search
        # Fix: 'heading' arg is deprecated/incorrect. Using positional.
        query = self.tbl.search(current_vector)

        # Enforce Causality (Backtesting)
        if cutoff_timestamp:
            # LanceDB/Arrow SQL filter requires explicit TIMESTAMP literal or compatible string
            ts_str = cutoff_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            query = query.where(f"timestamp < TIMESTAMP '{ts_str}'")

        results = query.limit(top_k).to_df()

        if results.empty:
            return {"weighted_outcome": 0.0, "confidence": 0.0, "matches": []}

        # Calculate Weighted Outcome
        # LanceDB 'dist' column
        if "_distance" in results.columns:
            results["similarity"] = 1 / (1 + results["_distance"])
        else:
            results["similarity"] = 1.0  # Fallback

        total_weight = results["similarity"].sum()
        weighted_outcome = (
            (results["outcome"] * results["similarity"]).sum() / total_weight
            if total_weight > 0
            else 0.0
        )

        matches = results[["symbol", "timestamp", "outcome", "similarity"]].to_dict(
            orient="records"
        )

        return {
            "weighted_outcome": float(weighted_outcome),
            "confidence": float(results["similarity"].mean()),
            "matches": matches,
        }

    def add_patterns(self, data: List[Dict[str, Any]]):
        """
        Batch ingest patterns into LanceDB.

        Args:
           data: List of dicts with keys: vector, symbol, timestamp, outcome.
        """
        if not data:
            return

        self.tbl.add(data)
        logger.info(f"Ingested {len(data)} patterns into Memory.")

    def get_latest_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the most recent record."""
        # This is expensive in LanceDB if not indexed or managed.
        # For now, simplistic scan or query.
        # Faster: Keep a separate metadata file/table.
        # Fallback: Query sorted limit 1.
        try:
            # LanceDB SQL-like query capability via DuckDB integration usually
            # Or just sort by timestamp desc limit 1
            # Note: TBL.search() is for vectors. TBL.to_lance() -> dataset -> .take?
            # Easiest: use to_pandas() with limit if supported or just assume empty for now for "backfill all"
            # Optimization: self.tbl.search(None).limit(1).to_pydantic() doesn't sort.

            # Temporary hack: return None to force backfill or check head.
            # Ideally we have a 'metadata' table.
            return None  # Force full check or implement better logic in Daemon
        except Exception as e:
            logger.error(f"Error getting latest timestamp: {e}")
            return None

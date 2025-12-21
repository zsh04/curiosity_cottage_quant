import logging
import json
import lancedb
from typing import List, Dict, Any
from datetime import datetime
from opentelemetry import trace
from app.core import metrics as business_metrics
from app.core.models import MarketStateEmbedding
import os

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class MemoryService:
    """
    Quantum Memory Service (Cloud Cortex Edition).
    Responsibility:
    1. Embed Market States (Physics + Sentiment) into vectors.
    2. Store them in LanceDB (Local Vector DB).
    3. Retrieve similar historical outcomes (RAG) to ground LLM reasoning.
    """

    def __init__(self, db_path: str = "data/lancedb"):
        try:
            from sentence_transformers import SentenceTransformer

            # Using standard lightweight model
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info(
                "MemoryService: Connected to Local Embeddings (SentenceTransformer) 🧠"
            )
        except ImportError:
            logger.error("MemoryService: sentence-transformers not installed.")
            self.embedding_model = None

        # Initialize LanceDB
        try:
            os.makedirs(db_path, exist_ok=True)
            self.db = lancedb.connect(db_path)
            # Create table if not exists (OPEN_OR_CREATE logic handled by create_table with exist_ok)
            # We map the Pydantic model to the table schema
            self.table_name = "market_state_embeddings"

            # LanceDB create_table expects data to infer schema or explicit schema
            # We use pydantic integration to create empty table if needed is tricker
            # actually .create_table(name, schema=Model) works in newer versions
            # Check if table exists
            if self.table_name in self.db.table_names():
                self.table = self.db.open_table(self.table_name)
            else:
                # Create empty table using the Pydantic schema
                self.table = self.db.create_table(
                    self.table_name, schema=MarketStateEmbedding
                )

            logger.info(f"MemoryService: Connected to LanceDB at {db_path} 💾")
        except Exception as e:
            logger.error(f"MemoryService: LanceDB Init Failed: {e}")
            self.db = None
            self.table = None

    @tracer.start_as_current_span("memory_embed_state")
    def embed_state(
        self, symbol: str, physics: Dict[str, Any], sentiment: Dict[str, Any]
    ) -> List[float]:
        """
        Convert complex state into a single vector.
        """
        if not self.embedding_model:
            return []

        # Construct textual representation of the Quantum State
        state_text = (
            f"Asset: {symbol}. "
            f"Regime: {physics.get('regime', 'Unknown')} (Alpha={physics.get('alpha', 0):.2f}). "
            f"Velocity: {physics.get('velocity', 0):.4f}. "
            f"Acceleration: {physics.get('acceleration', 0):.4f}. "
            f"Sentiment: {sentiment.get('label', 'Neutral')} (Score={sentiment.get('score', 0):.2f})."
        )

        try:
            # Encode returns numpy array, convert to list
            vector = self.embedding_model.encode(state_text).tolist()
            return vector
        except Exception as e:
            logger.error(f"MemoryService: Embedding generation failed: {e}")
            return []

    @tracer.start_as_current_span("memory_save_regime")
    def save_regime(
        self, symbol: str, physics: Dict[str, Any], sentiment: Dict[str, Any]
    ):
        """
        Save the current state to the 'market_state_embeddings' table.
        """
        if self.table is None:
            return

        embedding = self.embed_state(symbol, physics, sentiment)
        if not embedding or len(embedding) == 0:
            logger.debug("MemoryService: Skipping save (no embedding generated).")
            return

        metadata = {"physics": physics, "sentiment": sentiment}

        try:
            record = MarketStateEmbedding(
                vector=embedding,
                symbol=symbol,
                timestamp=datetime.now(),
                metadata=json.dumps(metadata),
            )

            # LanceDB add expects list of items
            self.table.add([record])

            logger.info(f"MemoryService: Saved regime for {symbol}.")
            business_metrics.memory_operations.add(1, {"op": "save", "symbol": symbol})

        except Exception as e:
            logger.error(f"MemoryService: Save failed: {e}")

    @tracer.start_as_current_span("memory_retrieve_similar")
    def retrieve_similar(
        self,
        symbol: str,
        physics: Dict[str, Any],
        sentiment: Dict[str, Any],
        k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find the top-k most similar historical market states.
        """
        if self.table is None:
            return []

        embedding = self.embed_state(symbol, physics, sentiment)
        if not embedding or len(embedding) == 0:
            return []

        results = []
        try:
            # LanceDB Search
            search_res = self.table.search(embedding).limit(k).to_list()

            for row in search_res:
                # row is a dict usually matching schema + _distance
                results.append(
                    {
                        "timestamp": row["timestamp"],
                        "symbol": row["symbol"],
                        "metadata": json.loads(row["metadata"]),
                        "distance": float(row.get("_distance", 0.0)),
                    }
                )

            logger.info(f"MemoryService: Retrieved {len(results)} similar regimes.")
            business_metrics.memory_operations.add(
                1, {"op": "retrieve", "symbol": symbol}
            )
            return results

        except Exception as e:
            logger.error(f"MemoryService: Retrieval failed: {e}")
            return []

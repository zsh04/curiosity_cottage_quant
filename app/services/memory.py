import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import text
from app.dal.database import SessionLocal
from opentelemetry import trace
from app.core import metrics as business_metrics
import os

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class MemoryService:
    """
    Quantum Memory Service (Cloud Cortex Edition).
    Responsibility:
    1. Embed Market States (Physics + Sentiment) into vectors.
    2. Store them in TimescaleDB (with pgvector).
    3. Retrieve similar historical outcomes (RAG) to ground LLM reasoning.

    NOTE: Embeddings currently disabled (Gemini Rolled Back).
    """

    def __init__(self):
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
        embedding = self.embed_state(symbol, physics, sentiment)
        if not embedding or len(embedding) == 0:
            logger.debug("MemoryService: Skipping save (no embedding generated).")
            return

        metadata = {"physics": physics, "sentiment": sentiment}

        # Use synchronous session for DB write
        session = SessionLocal()
        try:
            # Construct SQL with vector casting
            # Postgres pgvector expects '[...]' format.
            query = text("""
                INSERT INTO market_state_embeddings (timestamp, symbol, metadata, embedding)
                VALUES (NOW(), :symbol, :metadata, :embedding ::vector)
            """)

            session.execute(
                query,
                {
                    "symbol": symbol,
                    "metadata": json.dumps(metadata),
                    "embedding": str(embedding),
                },
            )
            session.commit()
            logger.info(f"MemoryService: Saved regime for {symbol}.")
            business_metrics.memory_operations.add(1, {"op": "save", "symbol": symbol})

        except Exception as e:
            logger.error(f"MemoryService: Save failed: {e}")
            session.rollback()
        finally:
            session.close()

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
        embedding = self.embed_state(symbol, physics, sentiment)
        if not embedding or len(embedding) == 0:
            return []

        session = SessionLocal()
        results = []
        try:
            # KNN Search using Cosine Distance (<=> operator)
            # We want the SMALLEST distance (most similar)
            query = text("""
                SELECT timestamp, symbol, metadata, (embedding <=> :query_vec ::vector) as distance
                FROM market_state_embeddings
                WHERE symbol = :symbol
                ORDER BY distance ASC
                LIMIT :k
            """)

            rows = session.execute(
                query, {"symbol": symbol, "query_vec": str(embedding), "k": k}
            ).fetchall()

            for row in rows:
                results.append(
                    {
                        "timestamp": row.timestamp,
                        "symbol": row.symbol,
                        "metadata": row.metadata,
                        "distance": float(row.distance),
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
        finally:
            session.close()

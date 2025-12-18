import logging
import os
from sqlalchemy import create_engine, text
from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FixSchema")


def fix_schema():
    """
    Drops the market_state_embeddings table and recreates it with vector(384).
    """
    logger.info("Attempting to fix vector schema...")

    # Connection string
    # Try to use the one from settings or construct it
    # settings.SQLALCHEMY_DATABASE_URI might be set
    db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    if not db_url:
        logger.error("DATABASE_URL not found.")
        return

    engine = create_engine(db_url)

    drop_query = text("DROP TABLE IF EXISTS market_state_embeddings CASCADE;")

    create_query = text("""
    CREATE TABLE IF NOT EXISTS market_state_embeddings (
        timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        symbol      TEXT NOT NULL,
        metadata    JSONB DEFAULT '{}'::jsonb,
        embedding   vector(384)
    );
    """)

    hypertable_query = text(
        "SELECT create_hypertable('market_state_embeddings', 'timestamp', if_not_exists => TRUE);"
    )

    hnsw_index_query = text("""
    CREATE INDEX IF NOT EXISTS idx_market_embeddings_hnsw 
    ON market_state_embeddings USING hnsw (embedding vector_cosine_ops);
    """)

    btree_index_query = text("""
    CREATE INDEX IF NOT EXISTS idx_market_embeddings_symbol_time 
    ON market_state_embeddings (symbol, timestamp DESC);
    """)

    with engine.connect() as conn:
        logger.info("Dropping table...")
        conn.execute(drop_query)
        logger.info("Recreating table with vector(384)...")
        conn.execute(create_query)
        logger.info("Converting to hypertable...")
        conn.execute(hypertable_query)
        logger.info("Creating HNSW index...")
        conn.execute(hnsw_index_query)
        logger.info("Creating B-Tree index...")
        conn.execute(btree_index_query)
        conn.commit()

    logger.info("✅ Schema fixed successfully.")


if __name__ == "__main__":
    fix_schema()

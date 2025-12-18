-- Protocol #4: Quantum Memory (Vector Embeddings)
-- Auto-executed on container startup via /docker-entrypoint-initdb.d/

-- Step 1: Enable AI and Vector Extensions
-- 'vector' provides the vector data type and distance metrics (L2, Cosine)
-- 'ai' (pgai) provides integration with LLM models for embedding generation (optional, but requested)
CREATE EXTENSION IF NOT EXISTS vector CASCADE;
CREATE EXTENSION IF NOT EXISTS ai CASCADE;

-- Step 2: Create Market State Embeddings Table
-- Stores the "Quantum State" (Physics + Sentiment) as a high-dimensional vector.
-- Using 1536 dimensions (compatible with OpenAI text-embedding-3-small/large or ada-002)
CREATE TABLE IF NOT EXISTS market_state_embeddings (
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol      TEXT NOT NULL,
    
    -- Metadata stored as JSONB for flexible queries (e.g., specific regime tags)
    metadata    JSONB DEFAULT '{}'::jsonb,
    
    -- The Quantum State Vector
    embedding   vector(384)
);

-- Step 3: Convert to Hypertable (TimescaleDB)
-- We partition by time because market regimes are time-dependent.
SELECT create_hypertable('market_state_embeddings', 'timestamp', if_not_exists => TRUE);

-- Step 4: Create HNSW Index for Fast Similarity Search
-- HNSW (Hierarchical Navigable Small World) is critical for performance on large vector sets.
-- cosine distance (<=>) is standard for normalized embeddings.
CREATE INDEX IF NOT EXISTS idx_market_embeddings_hnsw 
ON market_state_embeddings USING hnsw (embedding vector_cosine_ops);

-- Step 5: Standard Index on Symbol for lookups
CREATE INDEX IF NOT EXISTS idx_market_embeddings_symbol_time 
ON market_state_embeddings (symbol, timestamp DESC);

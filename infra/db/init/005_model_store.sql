-- Step 8: Model Store (Binary Blobs)
-- Stores serialized model states (Pickle/ONNX) for agent persistence.

CREATE TABLE IF NOT EXISTS model_checkpoints (
    id SERIAL PRIMARY KEY,
    agent_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    blob BYTEA NOT NULL
);

-- Index for fast retrieval of latest checkpoint per agent
CREATE INDEX IF NOT EXISTS idx_model_checkpoints_agent_time 
ON model_checkpoints (agent_name, created_at DESC);

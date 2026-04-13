CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    source_type TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_id VARCHAR UNIQUE
);

ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_id VARCHAR UNIQUE;

CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding vector(1536), -- text-embedding-3-small outputs 1536 dimensions
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Optimize similarity search via HNSW index (requires pgvector 0.5+)
CREATE INDEX IF NOT EXISTS embeddings_embedding_idx ON embeddings USING hnsw (embedding vector_cosine_ops);

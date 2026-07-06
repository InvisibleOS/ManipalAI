-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents Metadata Table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    uploaded_by UUID, -- Can be NULL or reference a users table
    upload_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Vector Embeddings Table (pgvector)
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(768), -- Match gemini-embedding-001 dimensions (768)
    chunk_index INTEGER
);

-- Announcements (High Priority Vectorized Context)
CREATE TABLE IF NOT EXISTS announcements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    posted_by UUID,
    embedding vector(768), -- Match gemini-embedding-001 dimensions (768)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- IVFFlat Indexes for Fast Vector Search (Cosine Similarity)
CREATE INDEX IF NOT EXISTS idx_document_embeddings ON document_embeddings 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_announcements_embeddings ON announcements 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Similarity search functions for RAG retrieval (used by frontend API via Supabase RPC)
CREATE OR REPLACE FUNCTION match_announcements(
  query_embedding vector(768),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  title varchar,
  content text,
  similarity float
)
LANGUAGE sql STABLE AS $$
  SELECT
    announcements.title,
    announcements.content,
    1 - (announcements.embedding <=> query_embedding) AS similarity
  FROM announcements
  WHERE 1 - (announcements.embedding <=> query_embedding) > match_threshold
  ORDER BY announcements.embedding <=> query_embedding
  LIMIT match_count;
$$;

CREATE OR REPLACE FUNCTION match_document_embeddings(
  query_embedding vector(768),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  title varchar,
  content text,
  similarity float
)
LANGUAGE sql STABLE AS $$
  SELECT
    documents.title,
    document_embeddings.content,
    1 - (document_embeddings.embedding <=> query_embedding) AS similarity
  FROM document_embeddings
  JOIN documents ON documents.id = document_embeddings.document_id
  WHERE 1 - (document_embeddings.embedding <=> query_embedding) > match_threshold
  ORDER BY document_embeddings.embedding <=> query_embedding
  LIMIT match_count;
$$;

import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from config.settings import settings
from api.database import get_db

logger = logging.getLogger(__name__)

class CodeEmbedder:
    """
    Production-grade code embedding manager using PostgreSQL pgvector.
    Stores code snippet embeddings and provides semantic search capabilities.
    """
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the code embedder and ensure pgvector is ready."""
        self.model = SentenceTransformer(model_name)
        self._initialize_pgvector()

    def _initialize_pgvector(self):
        """Enable pgvector extension and create the embeddings table."""
        try:
            # Use a temporary session to initialize the extension and table
            # This is typically handled by Alembic, but we ensure it here for reliability
            from api.database import engine
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS code_embeddings (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        snippet_id TEXT NOT NULL,
                        embedding vector(384),
                        code TEXT NOT NULL,
                        metadata JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_code_embeddings_vector ON code_embeddings USING hnsw (embedding vector_cosine_ops);"))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize pgvector: {e}")

    def generate_embedding(self, code: str) -> List[float]:
        """Generate embedding for a code snippet."""
        processed = self._preprocess_code(code)
        embedding = self.model.encode(processed)
        return embedding.tolist()

    def add_code_snippet(self, db: Session, code: str, snippet_id: str, metadata: Optional[Dict] = None):
        """Add a code snippet to the pgvector database."""
        embedding = self.generate_embedding(code)

        try:
            db.execute(
                text("INSERT INTO code_embeddings (snippet_id, embedding, code, metadata) VALUES (:sid, :emb, :code, :meta) "
                     "ON CONFLICT (snippet_id) DO UPDATE SET embedding = :emb, code = :code, metadata = :meta"),
                {"sid": snippet_id, "emb": embedding, "code": code, "meta": metadata or {}}
            )
            db.commit()
        except Exception as e:
            logger.error(f"Error adding snippet {snippet_id} to pgvector: {e}")
            db.rollback()

    def find_similar(self, db: Session, code: str, n_results: int = 5, threshold: float = 0.7) -> List[Dict]:
        """Find similar code snippets using cosine similarity in pgvector."""
        embedding = self.generate_embedding(code)

        try:
            # pgvector uses <-> for L2 distance, <=> for cosine distance.
            # Cosine similarity = 1 - cosine distance.
            query = text("""
                SELECT code, metadata, 1 - (embedding <=> :emb) as similarity
                FROM code_embeddings
                WHERE 1 - (embedding <=> :emb) >= :threshold
                ORDER BY similarity DESC
                LIMIT :limit
            """)

            results = db.execute(query, {"emb": embedding, "threshold": threshold, "limit": n_results}).fetchall()

            return [
                {"code": row[0], "metadata": row[1], "similarity": float(row[2])}
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error querying similar snippets: {e}")
            return []

    def calculate_similarity(self, code1: str, code2: str) -> float:
        """Calculate cosine similarity between two code snippets."""
        emb1 = np.array(self.generate_embedding(code1))
        emb2 = np.array(self.generate_embedding(code2))

        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(emb1, emb2) / (norm1 * norm2))

    def _preprocess_code(self, code: str) -> str:
        """Preprocess code for embedding."""
        lines = [line.strip() for line in code.split('\n')]
        processed = ' '.join(line for line in lines if line)
        return processed[:512] if len(processed) > 512 else processed

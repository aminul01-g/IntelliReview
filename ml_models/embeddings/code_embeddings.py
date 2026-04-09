from typing import List, Dict, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

class CodeEmbedder:
    """Generate and manage code embeddings for similarity detection."""
    
    def __init__(self, model_name: str = "microsoft/codebert-base"):
        """Initialize the code embedder."""
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Initialize ChromaDB for vector storage
        self.chroma_client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="./chroma_db"
        ))
        
        # Create or get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="code_snippets",
            metadata={"description": "Code snippet embeddings"}
        )
    
    def generate_embedding(self, code: str) -> np.ndarray:
        """Generate embedding for a code snippet."""
        # Preprocess code
        processed = self._preprocess_code(code)
        
        # Generate embedding
        embedding = self.model.encode(processed)
        
        return embedding
    
    def add_code_snippet(self, code: str, snippet_id: str, metadata: Dict = None):
        """Add a code snippet to the vector database."""
        embedding = self.generate_embedding(code)
        
        self.collection.add(
            embeddings=[embedding.tolist()],
            documents=[code],
            ids=[snippet_id],
            metadatas=[metadata or {}]
        )
    
    def find_similar(self, code: str, n_results: int = 5, threshold: float = 0.7) -> List[Dict]:
        """Find similar code snippets."""
        embedding = self.generate_embedding(code)
        
        results = self.collection.query(
            query_embeddings=[embedding.tolist()],
            n_results=n_results
        )
        
        similar_snippets = []
        
        if results['distances'] and results['documents']:
            for i, (distance, doc, metadata) in enumerate(zip(
                results['distances'][0],
                results['documents'][0],
                results['metadatas'][0]
            )):
                similarity = 1 - distance  # Convert distance to similarity
                
                if similarity >= threshold:
                    similar_snippets.append({
                        'code': doc,
                        'similarity': round(similarity, 3),
                        'metadata': metadata
                    })
        
        return similar_snippets
    
    def calculate_similarity(self, code1: str, code2: str) -> float:
        """Calculate similarity between two code snippets."""
        emb1 = self.generate_embedding(code1)
        emb2 = self.generate_embedding(code2)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        
        return float(similarity)
    
    def _preprocess_code(self, code: str) -> str:
        """Preprocess code for embedding."""
        # Remove excessive whitespace
        lines = [line.strip() for line in code.split('\n')]
        processed = ' '.join(line for line in lines if line)
        
        # Limit length
        if len(processed) > 512:
            processed = processed[:512]
        
        return processed

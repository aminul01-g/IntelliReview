"""
Lightweight in-memory RAG (Retrieval-Augmented Generation) context builder.

Instead of depending on heavy ChromaDB + SentenceTransformers (which add ~2GB to Docker),
this module uses a fast TF-IDF cosine similarity approach to find related files within
an uploaded project. This gives the LLM cross-file awareness without external dependencies.
"""

import re
import math
from typing import List, Dict, Optional
from collections import Counter


class ProjectContextBuilder:
    """
    Builds cross-file context for a project upload.
    
    When a user uploads a folder, this class indexes all files and can answer:
    "Given file X, which other files in this project are most related to it?"
    
    This enables the LLM to review code with full project awareness instead of
    evaluating each file in isolation.
    """
    
    def __init__(self):
        self._file_index: List[Dict] = []
        self._tfidf_vectors: List[Dict[str, float]] = []
        self._idf_cache: Dict[str, float] = {}
    
    def index_project(self, files: List[Dict]) -> None:
        """
        Index all files in the uploaded project for similarity search.
        
        Args:
            files: List of dicts with keys: 'filename', 'content', 'language'
        """
        self._file_index = files
        
        # Step 1: Tokenize each file into a bag of meaningful code tokens
        doc_tokens = []
        for f in files:
            tokens = self._extract_tokens(f["content"], f.get("filename", ""))
            doc_tokens.append(tokens)
        
        # Step 2: Compute IDF (Inverse Document Frequency) across the project
        num_docs = len(files)
        all_terms = set()
        for tokens in doc_tokens:
            all_terms.update(tokens.keys())
        
        self._idf_cache = {}
        for term in all_terms:
            doc_count = sum(1 for tokens in doc_tokens if term in tokens)
            self._idf_cache[term] = math.log((num_docs + 1) / (doc_count + 1)) + 1
        
        # Step 3: Compute TF-IDF vector for each file
        self._tfidf_vectors = []
        for tokens in doc_tokens:
            total = sum(tokens.values()) or 1
            vec = {}
            for term, count in tokens.items():
                tf = count / total
                vec[term] = tf * self._idf_cache.get(term, 1.0)
            self._tfidf_vectors.append(vec)
    
    def get_related_files(self, file_index: int, top_k: int = 5) -> List[Dict]:
        """
        Find the top-k most related files to the file at the given index.
        
        Returns a list of dicts with 'filename', 'similarity', and 'content' (truncated).
        """
        if not self._tfidf_vectors or file_index >= len(self._tfidf_vectors):
            return []
        
        query_vec = self._tfidf_vectors[file_index]
        similarities = []
        
        for i, vec in enumerate(self._tfidf_vectors):
            if i == file_index:
                continue
            sim = self._cosine_similarity(query_vec, vec)
            if sim > 0.05:  # Minimum relevance threshold
                similarities.append((i, sim))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, sim in similarities[:top_k]:
            f = self._file_index[idx]
            results.append({
                "filename": f["filename"],
                "similarity": round(sim, 3),
                "language": f.get("language", "unknown"),
                "content_preview": f["content"][:600],  # First 600 chars as context
            })
        
        return results
    
    def build_context_string(self, file_index: int, top_k: int = 3) -> Optional[str]:
        """
        Build a formatted context string for the LLM prompt.
        
        Returns a string like:
          "Related files in this project:
           1. src/models/user.py (similarity: 0.82): [first 400 chars of code]
           2. src/api/routes.py (similarity: 0.71): [first 400 chars of code]"
        
        Returns None if no related files are found.
        """
        related = self.get_related_files(file_index, top_k=top_k)
        if not related:
            return None
        
        lines = ["Related files in this project (for cross-file context):"]
        for i, r in enumerate(related, 1):
            lines.append(
                f"\n--- {i}. {r['filename']} ({r['language']}, similarity: {r['similarity']}) ---\n"
                f"```{r['language']}\n{r['content_preview']}\n```"
            )
        
        return "\n".join(lines)
    
    def _extract_tokens(self, code: str, filename: str) -> Counter:
        """
        Extract meaningful tokens from source code for similarity matching.
        
        This extracts:
        - Identifiers (variable names, function names, class names)
        - Import paths
        - String literals (API endpoints, table names)
        - File path components
        """
        tokens = Counter()
        
        # Extract identifiers (camelCase and snake_case aware)
        identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', code)
        for ident in identifiers:
            # Split camelCase: "getUserName" -> ["get", "user", "name"]
            parts = re.sub(r'([a-z])([A-Z])', r'\1_\2', ident).lower().split('_')
            for part in parts:
                if len(part) > 2 and part not in _STOPWORDS:
                    tokens[part] += 1
        
        # Extract import paths
        import_matches = re.findall(
            r'(?:import|from|require|include)\s+["\']?([a-zA-Z0-9_.\/]+)', code
        )
        for imp in import_matches:
            tokens[imp.lower()] += 3  # Imports are high-signal tokens
        
        # Extract string literals (API routes, table names, etc.)
        string_matches = re.findall(r'["\']([a-zA-Z0-9_/.-]{3,50})["\']', code)
        for s in string_matches:
            tokens[s.lower()] += 2
        
        # Add filename components as context
        path_parts = re.split(r'[/\\.]', filename.lower())
        for part in path_parts:
            if len(part) > 2 and part not in _STOPWORDS:
                tokens[part] += 2
        
        return tokens
    
    def _cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        """Compute cosine similarity between two sparse TF-IDF vectors."""
        # Only iterate over shared terms for efficiency
        shared_terms = set(vec_a.keys()) & set(vec_b.keys())
        if not shared_terms:
            return 0.0
        
        dot_product = sum(vec_a[t] * vec_b[t] for t in shared_terms)
        
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


# Common code stopwords to ignore during tokenization
_STOPWORDS = frozenset({
    "the", "and", "for", "not", "this", "that", "with", "from", "import",
    "return", "self", "none", "true", "false", "def", "class", "if", "else",
    "elif", "try", "except", "finally", "while", "break", "continue",
    "pass", "raise", "yield", "lambda", "global", "nonlocal", "assert",
    "del", "print", "input", "int", "str", "float", "bool", "list", "dict",
    "set", "tuple", "len", "range", "enumerate", "zip", "map", "filter",
    "var", "let", "const", "function", "async", "await", "new", "null",
    "undefined", "void", "public", "private", "protected", "static",
    "final", "abstract", "interface", "extends", "implements", "throws",
    "string", "number", "boolean", "object", "array", "any", "type",
    "export", "default", "module", "require", "include", "using",
    "namespace", "struct", "enum", "typedef", "sizeof", "unsigned",
    "signed", "char", "short", "long", "double", "volatile", "extern",
    "register", "auto", "inline", "virtual", "override", "template",
})

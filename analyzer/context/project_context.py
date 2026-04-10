"""
LLM-based Context Analyzer.

Uses a large language model (e.g., Qwen/Qwen3-32B) to dynamically deduce
conceptual relationships and data flow dependencies between project files.
"""

import math
import os
import json
import logging
import re
from typing import List, Dict, Optional
from collections import Counter

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

logger = logging.getLogger(__name__)


class ProjectContextBuilder:
    """
    Builds cross-file context for a project upload.
    
    When a user uploads a folder, this class indexes all files and can answer:
    "Given file X, which other files in this project are most related to it?"
    
    This enables the LLM to review code with full project awareness instead of
    evaluating each file in isolation.
    """
    
    def __init__(self, model_name: str = "Qwen/Qwen3-32B", api_key: str = None):
        self._file_index: List[Dict] = []
        self._related_map_cache: Dict[str, List[str]] = {}
        
        self.model_name = os.getenv('HUGGINGFACE_CONTEXT_MODEL', model_name)
        self.api_key = api_key or os.getenv('HUGGINGFACE_API_KEY')
        
        if not InferenceClient:
            logger.warning("huggingface_hub not installed. Context logic will fail.")
            self.client = None
        else:
            self.client = InferenceClient(token=self.api_key)
    
    def index_project(self, files: List[Dict]) -> None:
        """
        Cache the files in memory for context LLM mapping.
        
        Args:
            files: List of dicts with keys: 'filename', 'content', 'language'
        """
        self._file_index = files
        self._related_map_cache = {}
    
    def get_related_files(self, file_index: int, top_k: int = 5) -> List[Dict]:
        """
        Use the LLM to deduce the top-k conceptually related files.
        """
        if not self.client or file_index >= len(self._file_index):
            return []
            
        target_file = self._file_index[file_index]
        target_name = target_file["filename"]
        
        # Return cached maps to avoid duplicate heavy LLM calls
        if target_name in self._related_map_cache:
            related_names = self._related_map_cache[target_name]
            return [f for f in self._file_index if f["filename"] in related_names][:top_k]
        
        # Extract small representation of other files to save context limit
        other_files = []
        for i, f in enumerate(self._file_index):
            if i != file_index:
                other_files.append(f"- {f['filename']} ({f.get('language', 'unknown')})")
                
        if not other_files:
            return []

        prompt = f"""You are an elite Software Architect. We are analyzing target file: {target_name}.
Here is a snippet of its core logic:
```
{target_file['content'][:500]}
```

Here are the other files in the project workspace:
{chr(10).join(other_files)}

Deduce the top {top_k} files in the workspace that are highly dependent, conceptually linked, or imported by this target file.
Return ONLY a JSON array of strings matching the exact filenames. Return [] if none are related."""

        try:
            response = self.client.text_generation(
                prompt,
                model=self.model_name,
                max_new_tokens=150,
                temperature=0.1
            )
            
            response = response.strip()
            if response.startswith("```json"): response = response[7:]
            if response.startswith("```"): response = response[3:]
            if response.endswith("```"): response = response[:-3]
            response = response.strip()
            
            related_names = json.loads(response)
            if isinstance(related_names, list):
                self._related_map_cache[target_name] = related_names
                results = []
                for fname in related_names[:top_k]:
                    matched = next((x for x in self._file_index if x["filename"] == fname), None)
                    if matched:
                        results.append({
                            "filename": matched["filename"],
                            "similarity": 0.9, # Inferred High Priority
                            "language": matched.get("language", "unknown"),
                            "content_preview": matched["content"][:600]
                        })
                return results
                
        except Exception as e:
            logger.warning(f"LLM Context Generator failed for {target_name}: {e}")
            
        return []
    
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

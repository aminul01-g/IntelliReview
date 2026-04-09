"""Machine learning models for code analysis."""

try:
    from .generators.suggestion_generator import SuggestionGenerator
except ImportError:
    SuggestionGenerator = None

try:
    from .embeddings.code_embeddings import CodeEmbedder
except ImportError:
    CodeEmbedder = None

__all__ = ['CodeEmbedder', 'SuggestionGenerator']

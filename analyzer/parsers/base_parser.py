from abc import ABC, abstractmethod
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ParsedNode:
    """Represents a parsed AST node."""
    type: str
    name: str
    line_start: int
    line_end: int
    complexity: int = 1
    children: List['ParsedNode'] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.metadata is None:
            self.metadata = {}

class BaseParser(ABC):
    """Base class for language-specific parsers."""
    
    @abstractmethod
    def parse(self, code: str, filename: str = "") -> ParsedNode:
        """Parse source code and return AST."""
        pass
    
    @abstractmethod
    def extract_functions(self, ast: ParsedNode) -> List[ParsedNode]:
        """Extract all function definitions."""
        pass
    
    @abstractmethod
    def extract_classes(self, ast: ParsedNode) -> List[ParsedNode]:
        """Extract all class definitions."""
        pass
    
    def get_language(self) -> str:
        """Return the language this parser handles."""
        return self.__class__.__name__.replace('Parser', '').lower()


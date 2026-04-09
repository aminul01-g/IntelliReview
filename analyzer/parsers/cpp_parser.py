from typing import List
import re
from .base_parser import BaseParser, ParsedNode

class CppParser(BaseParser):
    """Parser for C++ source code (simplified version)."""
    
    def parse(self, code: str, filename: str = "") -> ParsedNode:
        """Parse C++ code into AST-like structure using regex."""
        lines = code.split('\n')
        root = ParsedNode(
            type='TranslationUnit',
            name=filename,
            line_start=1,
            line_end=len(lines)
        )
        
        # Extract classes and methods
        root.children.extend(self.extract_classes(code, root))
        # Also extract global functions
        root.children.extend(self.extract_functions(code, root))
        
        return root
    
    def extract_functions(self, code: str, ast_node: ParsedNode) -> List[ParsedNode]:
        """Extract function declarations using regex."""
        functions = []
        # Basic regex for C++ functions: [type] [name](args) {
        # This is a simplification; C++ syntax is complex.
        func_pattern = re.compile(r'(?:[\w&*<>]+(?:\s+[\w&*<>]+)*\s+)?(\w+)\s*\([^)]*\)\s*(?:const|override|noexcept|\s)*\s*\{')
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            # Skip lines that look like control flow
            if any(ctrl in line for ctrl in ['if', 'while', 'for', 'switch']):
                continue
                
            match = func_pattern.search(line)
            if match:
                func_name = match.group(1)
                # Avoid duplicates from class methods already found
                if any(f.name == func_name for f in functions):
                    continue
                    
                functions.append(ParsedNode(
                    type='FunctionDef',
                    name=func_name,
                    line_start=i + 1,
                    line_end=i + 5 # dummy end
                ))
        return functions
    
    def extract_classes(self, code: str, ast_node: ParsedNode) -> List[ParsedNode]:
        """Extract class/struct declarations using regex."""
        classes = []
        class_pattern = re.compile(r'(?:class|struct)\s+(\w+)\s*(?::\s*[\w\s,:]+)?\s*\{')
        
        lines = code.split('\n')
        for i, line in enumerate(lines):
            match = class_pattern.search(line)
            if match:
                class_name = match.group(1)
                cls_node = ParsedNode(
                    type='ClassDef',
                    name=class_name,
                    line_start=i + 1,
                    line_end=len(lines)
                )
                classes.append(cls_node)
        return classes

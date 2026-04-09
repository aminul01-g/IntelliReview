import ast
from typing import List, Dict, Any
from .base_parser import BaseParser, ParsedNode

class PythonParser(BaseParser):
    """Parser for Python source code."""
    
    def parse(self, code: str, filename: str = "") -> ParsedNode:
        """Parse Python code into AST."""
        try:
            tree = ast.parse(code, filename=filename)
            return self._convert_ast(tree)
        except SyntaxError as e:
            # Return dummy node on syntax error - let QualityDetector handle it
            return ParsedNode(
                type='SyntaxError',
                name='ParseError',
                line_start=getattr(e, 'lineno', 1),
                line_end=getattr(e, 'lineno', 1),
                metadata={'error': str(e), 'msg': e.msg}
            )
    
    def _convert_ast(self, node: ast.AST, parent_line: int = 0) -> ParsedNode:
        """Convert Python AST to ParsedNode."""
        node_type = node.__class__.__name__
        name = getattr(node, 'name', '')
        line_start = getattr(node, 'lineno', parent_line)
        line_end = getattr(node, 'end_lineno', line_start)
        
        parsed = ParsedNode(
            type=node_type,
            name=name,
            line_start=line_start,
            line_end=line_end,
            metadata={'raw_node': node}
        )
        
        # Process children
        for child in ast.iter_child_nodes(node):
            parsed.children.append(self._convert_ast(child, line_start))
        
        return parsed
    
    def extract_functions(self, ast_node: ParsedNode) -> List[ParsedNode]:
        """Extract all function definitions."""
        functions = []
        
        def visit(node: ParsedNode):
            if node.type == 'FunctionDef':
                functions.append(node)
            for child in node.children:
                visit(child)
        
        visit(ast_node)
        return functions
    
    def extract_classes(self, ast_node: ParsedNode) -> List[ParsedNode]:
        """Extract all class definitions."""
        classes = []
        
        def visit(node: ParsedNode):
            if node.type == 'ClassDef':
                classes.append(node)
            for child in node.children:
                visit(child)
        
        visit(ast_node)
        return classes
    
    def extract_imports(self, ast_node: ParsedNode) -> List[str]:
        """Extract all import statements."""
        imports = []
        
        def visit(node: ParsedNode):
            if node.type in ['Import', 'ImportFrom']:
                raw_node = node.metadata.get('raw_node')
                if isinstance(raw_node, ast.Import):
                    for alias in raw_node.names:
                        imports.append(alias.name)
                elif isinstance(raw_node, ast.ImportFrom):
                    module = raw_node.module or ''
                    for alias in raw_node.names:
                        imports.append(f"{module}.{alias.name}")
            
            for child in node.children:
                visit(child)
        
        visit(ast_node)
        return imports
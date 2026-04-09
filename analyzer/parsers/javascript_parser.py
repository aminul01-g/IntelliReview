import esprima
from typing import List, Dict, Any
from .base_parser import BaseParser, ParsedNode

class JavaScriptParser(BaseParser):
    """Parser for JavaScript source code."""
    
    def parse(self, code: str, filename: str = "") -> ParsedNode:
        """Parse JavaScript code into AST."""
        try:
            tree = esprima.parseScript(code, loc=True)
            return self._convert_ast(tree)
        except Exception as e:
            # Return dummy node on syntax error - let QualityDetector handle it
            return ParsedNode(
                type='SyntaxError',
                name='ParseError',
                line_start=1,
                line_end=1,
                metadata={'error': str(e)}
            )
    
    def _convert_ast(self, node: Any) -> ParsedNode:
        """Convert Esprima AST to ParsedNode."""
        node_type = node.type if hasattr(node, 'type') else 'Unknown'
        
        # Extract name
        name = ''
        if hasattr(node, 'id') and hasattr(node.id, 'name'):
            name = node.id.name
        elif hasattr(node, 'name'):
            name = node.name
        
        # Extract location
        line_start = 0
        line_end = 0
        if hasattr(node, 'loc') and node.loc:
            line_start = node.loc.start.line
            line_end = node.loc.end.line
        
        parsed = ParsedNode(
            type=node_type,
            name=name,
            line_start=line_start,
            line_end=line_end,
            metadata={'raw_node': node}
        )
        
        # Process children
        if hasattr(node, 'body'):
            if isinstance(node.body, list):
                for child in node.body:
                    parsed.children.append(self._convert_ast(child))
            else:
                parsed.children.append(self._convert_ast(node.body))
        
        return parsed
    
    def extract_functions(self, ast_node: ParsedNode) -> List[ParsedNode]:
        """Extract all function declarations."""
        functions = []
        
        def visit(node: ParsedNode):
            if node.type in ['FunctionDeclaration', 'ArrowFunctionExpression', 'FunctionExpression']:
                functions.append(node)
            for child in node.children:
                visit(child)
        
        visit(ast_node)
        return functions
    
    def extract_classes(self, ast_node: ParsedNode) -> List[ParsedNode]:
        """Extract all class declarations."""
        classes = []
        
        def visit(node: ParsedNode):
            if node.type == 'ClassDeclaration':
                classes.append(node)
            for child in node.children:
                visit(child)
        
        visit(ast_node)
        return classes

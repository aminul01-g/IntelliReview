import ast
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def extract_functions_from_snippet(code_snippet: str, language: str = "python") -> List[Dict]:
    """
    Attempts to parse a code snippet using AST to extract functions.
    If the snippet is incomplete (e.g., from a diff), it tries to salvage the AST
    by wrapping it or gracefully degrading.
    """
    if language.lower() not in ["python", ".py"]:
        # Fallback for non-python: just return the raw text block
        return [{"name": "snippet", "body": code_snippet, "type": "raw_block"}]

    try:
        # Try pure parse first
        tree = ast.parse(code_snippet)
    except SyntaxError:
        try:
            # Maybe it's just statements without a function? Let's wrap it in a dummy function
            wrapped = f"def __dummy_wrapper__():\n" + "\n".join(f"    {line}" for line in code_snippet.split('\n'))
            tree = ast.parse(wrapped)
        except SyntaxError:
            # If all fails, return raw block
            return [{"name": "unparseable_snippet", "body": code_snippet, "type": "raw_block"}]

    functions = []
    
    class FunctionExtractor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            # Do not extract the __dummy_wrapper__ itself, but its body is just the statements
            if node.name == "__dummy_wrapper__":
                self.generic_visit(node)
                return
            
            start_line = getattr(node, 'lineno', 1)
            end_line = getattr(node, 'end_lineno', start_line)
            
            # Extract the raw text
            lines = code_snippet.split('\n')
            # Handle 1-index offsets and possible wrapper shifts
            body_text = "\n".join(lines[max(0, start_line-1):end_line])
            
            functions.append({
                "name": node.name,
                "type": "FunctionDef",
                "body": body_text,
                "start_line": start_line,
                "end_line": end_line
            })
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            if node.name == "__dummy_wrapper__": return
            start_line = getattr(node, 'lineno', 1)
            end_line = getattr(node, 'end_lineno', start_line)
            lines = code_snippet.split('\n')
            body_text = "\n".join(lines[max(0, start_line-1):end_line])
            
            functions.append({
                "name": node.name,
                "type": "AsyncFunctionDef",
                "body": body_text,
                "start_line": start_line,
                "end_line": end_line
            })
            self.generic_visit(node)

    extractor = FunctionExtractor()
    extractor.visit(tree)

    # If no functions found (e.g. just a sequence of statements inside the dummy wrapper),
    # return the raw snippet as a single block so LLM has context.
    if not functions:
        return [{"name": "module_level_statements", "body": code_snippet, "type": "Statements"}]
        
    return functions

def map_diff_to_ast_context(hunks: List[Dict], language: str) -> List[Dict]:
    """
    Given parsed diff hunks containing 'added_lines' and 'context', 
    combines them to extract the logical function boundaries that were modified.
    """
    extracted_contexts = []
    for index, hunk in enumerate(hunks):
        # We merge context lines + added lines to give the AST parser maximum chance of succeeding
        reconstructed = []
        # Pre-context
        context_count = len(hunk.get("context", []))
        mid = context_count // 2
        
        pre_context = hunk["context"][:mid]
        post_context = hunk["context"][mid:]
        
        reconstructed.extend(pre_context)
        reconstructed.extend(hunk.get("added_lines", []))
        reconstructed.extend(post_context)
        
        snippet = "\n".join(reconstructed)
        if not snippet.strip():
            continue
            
        functions = extract_functions_from_snippet(snippet, language)
        for f in functions:
            extracted_contexts.append({
                "hunk_index": index,
                "context_name": f["name"],
                "context_type": f["type"],
                "code": f["body"]
            })
            
    return extracted_contexts

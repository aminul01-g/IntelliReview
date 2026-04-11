from typing import List, Dict, Pattern
import re
from ..parsers.base_parser import ParsedNode

class AntiPatternDetector:
    """Detect common anti-patterns in code."""
    
    # Pre-compile regex for performance
    MAGIC_NUMBER_REGEX: Pattern = re.compile(r'\b\d{2,}\b')
    
    def detect(self, code: str, ast: ParsedNode, language: str = "python") -> List[Dict]:
        """Detect anti-patterns."""
        issues: List[Dict] = []
        
        if language == "python":
            issues.extend(self._detect_python_antipatterns(code, ast))
        elif language == "javascript":
            issues.extend(self._detect_javascript_antipatterns(code, ast))
        elif language == "java":
            issues.extend(self._detect_java_antipatterns(code, ast))
        
        return issues
    
    def _detect_java_antipatterns(self, code: str, ast: ParsedNode) -> List[Dict]:
        """Detect Java-specific anti-patterns."""
        # Java detectors often look for similar structure as Python (God Class, Long Method)
        # Using the same logic since we've made the AST nodes consistent
        return self._detect_python_antipatterns(code, ast)
    
    def _detect_python_antipatterns(self, code: str, ast: ParsedNode) -> List[Dict]:
        """Detect Python-specific anti-patterns."""
        issues: List[Dict] = []
        lines = code.split('\n')
        
        # God Class (class with too many methods)
        classes = self._find_nodes_by_type(ast, 'ClassDef')
        for cls in classes:
            methods = [c for c in cls.children if c.type == 'FunctionDef']
            if len(methods) > 20:
                issues.append({
                    "type": "god_class",
                    "severity": "high",
                    "line": cls.line_start,
                    "message": f"Class '{cls.name}' has {len(methods)} methods (God Class)",
                    "suggestion": "Consider breaking this class into smaller, focused classes"
                })
        
        # Long Method
        functions = self._find_nodes_by_type(ast, 'FunctionDef')
        for func in functions:
            func_length = func.line_end - func.line_start
            if func_length > 50:
                issues.append({
                    "type": "long_method",
                    "severity": "medium",
                    "line": func.line_start,
                    "message": f"Method '{func.name}' is {func_length} lines long",
                    "suggestion": "Break this method into smaller, focused methods"
                })
        
        # Magic Numbers
        for i, line in enumerate(lines, 1):
            magic_numbers = self.MAGIC_NUMBER_REGEX.findall(line)
            for num in magic_numbers:
                if num not in ['100', '1000']:  # Common exceptions
                    issues.append({
                        "type": "magic_number",
                        "severity": "low",
                        "line": i,
                        "message": f"Magic number '{num}' found",
                        "suggestion": f"Replace with a named constant"
                    })
        
        # Asyncio blocks in loops (Phase 4 Depth)
        in_loop = False
        in_loop_indent = 0
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            
            if stripped.startswith("for ") or stripped.startswith("while "):
                in_loop = True
                in_loop_indent = indent
            elif in_loop and indent <= in_loop_indent and stripped:
                in_loop = False
                
            if in_loop and "await " in stripped:
                issues.append({
                    "type": "asyncio_loop_blocking",
                    "severity": "high",
                    "line": i,
                    "message": "Using 'await' inside a loop creates sequential blocking.",
                    "suggestion": "Gather tasks in a list and use 'await asyncio.gather(*tasks)' for concurrent execution."
                })
                
            if in_loop and ".objects." in stripped and ("filter" in stripped or "get" in stripped or "all" in stripped):
                issues.append({
                    "type": "orm_n_plus_one",
                    "severity": "critical",
                    "line": i,
                    "message": "Database query inside a loop (Django ORM N+1 Problem).",
                    "suggestion": "Move the query outside the loop or use 'select_related' / 'prefetch_related'."
                })
        
        # Nested loops (deep nesting)
        nested_depth, offending_line = self._check_nesting_depth(ast)
        if nested_depth > 3:
            issues.append({
                "type": "deep_nesting",
                "severity": "medium",
                "line": offending_line,
                "message": f"Code has nesting depth of {nested_depth}",
                "suggestion": "Refactor to reduce nesting complexity (consider using 'elif' or breaking into functions)"
            })
        
        return issues
    
    def _detect_javascript_antipatterns(self, code: str, ast: ParsedNode) -> List[Dict]:
        """Detect JavaScript-specific anti-patterns."""
        issues: List[Dict] = []
        lines = code.split('\n')
        
        # Callback Hell
        callback_depth = self._count_callback_depth(code)
        if callback_depth > 3:
            issues.append({
                "type": "callback_hell",
                "severity": "high",
                "line": 1,
                "message": f"Callback nesting depth of {callback_depth}",
                "suggestion": "Use Promises or async/await"
            })
        
        # == instead of ===
        for i, line in enumerate(lines, 1):
            if ' == ' in line and ' === ' not in line:
                issues.append({
                    "type": "weak_equality",
                    "severity": "medium",
                    "line": i,
                    "message": "Using '==' instead of '==='",
                    "suggestion": "Use strict equality '===' for type-safe comparisons"
                })
        
        # React Hooks Depth (Phase 4 Depth)
        full_code = " ".join(l.strip() for l in lines)
        # Match useEffect without a dependency array (e.g. useEffect(() => { ... }))
        if re.search(r'useEffect\s*\([^,\]]+\)\s*;', full_code) or re.search(r'useEffect\s*\([^,\]]+\)[^,]*\}\)', full_code):
             # Try to find the line
             for i, line in enumerate(lines, 1):
                 if 'useEffect' in line and ']' not in line:
                     issues.append({
                         "type": "react_hook_missing_deps",
                         "severity": "high",
                         "line": i,
                         "message": "useEffect is missing a dependency array, risking immense re-renders.",
                         "suggestion": "Add a dependency array '[]' to run once, or list exact dependencies."
                     })
                     break
        
        return issues
    
    def _find_nodes_by_type(self, node: ParsedNode, node_type: str) -> List[ParsedNode]:
        """Recursively find all nodes of a given type."""
        results: List[ParsedNode] = []
        
        if node.type == node_type:
            results.append(node)
        
        for child in node.children:
            results.extend(self._find_nodes_by_type(child, node_type))
        
        return results
    
    def _check_nesting_depth(self, node: ParsedNode, current_depth: int = 0) -> (int, int):
        """Calculate maximum nesting depth and return (max_depth, line_no)."""
        max_depth = current_depth
        offending_line = node.line_start
        
        control_flow_types = ['For', 'While', 'If', 'With', 'Try']
        
        if node.type in control_flow_types:
            current_depth += 1
            max_depth = current_depth
        
        for child in node.children:
            child_depth, child_line = self._check_nesting_depth(child, current_depth)
            
            # Heuristic for if-elif-else chain: 
            # If the current node is an If and child is also an If, don't double count if it's the only If child.
            # (In Python AST, 'elif' is an If node inside the 'orelse' block of another If node)
            if node.type == 'If' and child.type == 'If':
                 child_depth -= 1
            
            if child_depth > max_depth:
                max_depth = child_depth
                offending_line = child_line
        
        return max_depth, offending_line
    
    def _count_callback_depth(self, code: str) -> int:
        """Count callback nesting depth in JavaScript."""
        max_depth = 0
        current_depth = 0
        
        for char in code:
            if char == '{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == '}':
                current_depth -= 1
        
        return max_depth

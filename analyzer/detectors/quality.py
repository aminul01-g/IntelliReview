import ast
from typing import List, Dict
import io
import os
import tempfile
from pylint.lint import Run
from pylint.reporters.text import TextReporter

class QualityDetector:
    """Detect code quality issues and common bugs using static analysis."""

    def __init__(self):
        # We'll use a reporter that captures output in memory
        self.pylint_output = io.StringIO()
        self.reporter = TextReporter(self.pylint_output)

    def detect(self, code: str, filename: str = "temp.py", language: str = "python") -> List[Dict]:
        """Detect bugs and quality issues."""
        issues = []
        
        if language == "python":
            issues.extend(self._analyze_python(code, filename))
        elif language == "javascript":
            issues.extend(self._analyze_javascript(code))
        elif language == "java":
            issues.extend(self._analyze_java(code))
        elif language == "cpp" or language == "c":
            issues.extend(self._analyze_cpp(code))
        
        return issues

    def _analyze_cpp(self, code: str) -> List[Dict]:
        """Expert SQE quality checks for C/C++."""
        issues = []
        lines = code.split('\n')
        
        # 0. SYNTAX ERROR DETECTION (Critical!)
        syntax_issues = self._check_cpp_syntax_errors(code, lines)
        if syntax_issues:
            return syntax_issues  # Return immediately if syntax errors found
        
        # 1. Check for unsafe functions and common anti-patterns
        unsafe_funcs = ['strcpy', 'strcat', 'sprintf', 'gets', 'scanf']
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Anti-pattern: using namespace std
            if 'using namespace std' in stripped:
                issues.append({
                    "type": "code_quality",
                    "severity": "medium",
                    "line": i,
                    "message": "'using namespace std' pollutes the global namespace and can cause name collisions.",
                    "suggestion": "Remove 'using namespace std;' and use the 'std::' prefix explicitly (e.g., 'std::cout')."
                })
                
            # Performance: endl vs \n
            if '<< endl' in line or '<<endl' in line:
                issues.append({
                    "type": "performance",
                    "severity": "low",
                    "line": i,
                    "message": "Using 'endl' forces a stream flush, which can degrade performance.",
                    "suggestion": "Prefer using '\\n' for newlines unless you explicitly need to flush the output stream."
                })

            for func in unsafe_funcs:
                if f"{func}(" in line:
                    issues.append({
                        "type": "security",
                        "severity": "high",
                        "line": i,
                        "message": f"Use of unsafe function '{func}' detected. Potential buffer overflow.",
                        "suggestion": f"Use safer alternatives like '{func}n', 'snprintf', or 'std::string'."
                    })

        # 2. Memory Leak: 'new' without 'delete'
        if 'new ' in code and 'delete ' not in code and 'unique_ptr' not in code and 'shared_ptr' not in code:
             issues.append({
                "type": "bug",
                "severity": "high",
                "line": 1,
                "message": "Potential memory leak: 'new' is used but no corresponding 'delete' or smart pointer was found.",
                "suggestion": "Always pair 'new' with 'delete', or preferably use std::unique_ptr/std::shared_ptr."
            })

        # 3. Check for missing virtual destructor in classes
        if 'class' in code and 'virtual ~' not in code:
             issues.append({
                "type": "code_quality",
                "severity": "medium",
                "line": 1,
                "message": "Class detected without virtual destructor. This can cause UB during polymorphic deletion.",
                "suggestion": "Add a virtual destructor to base classes."
            })
            
        return issues

    def _analyze_python(self, code: str, filename: str) -> List[Dict]:
        """Analyze Python code for bugs and quality issues."""
        issues = []
        
        # 1. Custom AST-based checks
        try:
            tree = ast.parse(code)
            issues.extend(self._check_python_specifics(tree, code))
        except SyntaxError as e:
            # CRITICAL: Report syntax errors!
            issues.append({
                "type": "syntax_error",
                "severity": "critical",
                "line": e.lineno or 1,
                "message": f"Syntax Error: {str(e.msg)}",
                "suggestion": f"Fix the syntax error at line {e.lineno}: {e.text.strip() if e.text else 'Check your code syntax'}"
            })
            return issues  # Return immediately, can't analyze invalid syntax

        # 2. Use Pylint for broader checks using an isolated temporary file to prevent Errno 2
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_file:
            tmp_file.write(code)
            temp_path = tmp_file.name

        try:
            pylint_args = [
                temp_path,
                '--disable=all',
                '--enable=E,F',
                '--reports=n',
                '--score=n',
                '--jobs=4'
            ]
            
            output = io.StringIO()
            Run(pylint_args, reporter=TextReporter(output), exit=False)
            
            pylint_results = output.getvalue()
            for line in pylint_results.splitlines():
                if ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        try:
                            line_no = int(parts[1])
                            msg = ":".join(parts[2:]).strip()
                            
                            severity = "medium"
                            if "(E" in msg:
                                severity = "high"
                            elif "(W" in msg:
                                severity = "medium"
                                
                            issues.append({
                                "type": "code_quality",
                                "severity": severity,
                                "line": line_no,
                                "message": f"Pylint: {msg}",
                                "suggestion": "Fix this code quality issue."
                            })
                        except Exception as e:
                            pass
        except Exception as e:
            issues.append({
                "type": "error",
                "severity": "medium",
                "line": 1,
                "message": f"Pylint analysis failed: {str(e)}",
                "suggestion": ""
            })
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            
        return issues

    def _check_python_specifics(self, tree: ast.AST, code: str) -> List[Dict]:
        """Expert SQE checks for Python."""
        issues = []
        
        # Existing checks
        issues.extend(self._check_missing_args_and_uncalled_funcs(tree, code))
        
        # New SQE Checks
        for node in ast.walk(tree):
            # 1. Resource Leak: Opening file without 'with' or '.close()'
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'open':
                # Check if it's inside a 'with' statement
                parent = self._get_parent(tree, node)
                if not isinstance(parent, ast.withitem) and not self._is_assigned_and_closed(tree, node):
                    issues.append({
                        "type": "bug",
                        "severity": "high",
                        "line": node.lineno,
                        "message": "File opened without 'with' statement or explicit .close(). Potential resource leak.",
                        "suggestion": "Use 'with open(...) as f:' for automatic resource management."
                    })
            
            # 2. Concurrency: Global variable modification without Lock
            if isinstance(node, ast.Global):
                issues.append({
                    "type": "bug",
                    "severity": "medium",
                    "line": node.lineno,
                    "message": "Use of 'global' detected. In multi-threaded environments, this can lead to race conditions.",
                    "suggestion": "Avoid global state or use threading.Lock() to synchronize access."
                })

        return issues

    def _get_parent(self, tree, target):
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                if child is target:
                    return node
        return None

    def _is_assigned_and_closed(self, tree, open_node):
        # Very simplified check for variable assignment and subsequent .close()
        return False # Erring on the side of reporting

    def _check_missing_args_and_uncalled_funcs(self, tree: ast.AST, code: str) -> List[Dict]:
        """Perform specific AST checks for bugs."""
        issues = []
        
        # Track defined functions and their argument counts
        func_definitions = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_definitions[node.name] = {
                    "args_count": len(node.args.args),
                    "pos": node.lineno
                }

        # Track input() variables
        input_vars = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id == 'input':
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                input_vars.add(target.id)

        # Check call sites
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in func_definitions:
                        expected = func_definitions[func_name]["args_count"]
                        actual = len(node.args) + len(node.keywords)
                        if expected != actual:
                            issues.append({
                                "type": "bug",
                                "severity": "high",
                                "line": node.lineno,
                                "message": f"Function '{func_name}' expects {expected} arguments, but got {actual}",
                                "suggestion": f"Check the function definition at line {func_definitions[func_name]['pos']} and provide the correct arguments"
                            })
                
            # Check for name references that might be intended as calls (uncalled functions)
            elif isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Name):
                    if node.value.id in func_definitions:
                        issues.append({
                            "type": "bug",
                            "severity": "medium",
                            "line": node.lineno,
                            "message": f"Function '{node.value.id}' is referenced as an expression but not called",
                            "suggestion": f"Add parentheses '()' to call the function"
                        })
            
            # Check for comparison type mismatch (input() vs int)
            elif isinstance(node, ast.Compare):
                if isinstance(node.left, ast.Name) and node.left.id in input_vars:
                    for comparator in node.comparators:
                        if isinstance(comparator, ast.Constant) and isinstance(comparator.value, int):
                            issues.append({
                                "type": "bug",
                                "severity": "high",
                                "line": node.lineno,
                                "message": f"Comparing variable '{node.left.id}' (from input()) with an integer. input() returns a string.",
                                "suggestion": f"Convert the input to an integer using int({node.left.id})"
                            })
        
        return issues

    def _analyze_javascript(self, code: str) -> List[Dict]:
        """Expert SQE checks for JavaScript."""
        import esprima
        issues = []
        try:
            tree = esprima.parseScript(code, loc=True)
            for node in self._walk_esprima(tree):
                # 1. Memory Leak: Event listener without removal pattern
                if node.type == 'CallExpression' and \
                   node.callee.type == 'MemberExpression' and \
                   node.callee.property.name == 'addEventListener':
                    issues.append({
                        "type": "bug",
                        "severity": "medium",
                        "line": node.loc.start.line,
                        "message": "addEventListener detected. Ensure removeEventListener is called to prevent memory leaks.",
                        "suggestion": "Implement a cleanup mechanism (e.g., in useEffect return or beforeDestroy)."
                    })
                
                # 2. Unhandled Promise: No .catch() or try-catch
                if node.type == 'CallExpression' and node.callee.type == 'MemberExpression' and node.callee.property.name == 'then':
                    # Check if followed by .catch
                    # (Simplified check)
                    issues.append({
                        "type": "bug",
                        "severity": "medium",
                        "line": node.loc.start.line,
                        "message": "Promise .then() detected without immediate .catch(). Unhandled rejections can crash legacy environments.",
                        "suggestion": "Always append .catch() to promise chains."
                    })

                # Existing checks
                if node.type == 'BinaryExpression' and node.operator == '==':
                    issues.append({
                        "type": "code_quality",
                        "severity": "medium",
                        "line": node.loc.start.line,
                        "message": "Use of '==' instead of '===' (weak equality)",
                        "suggestion": "Use strict equality '==='"
                    })
        except Exception as e:
            # CRITICAL: Report JavaScript syntax errors!
            error_msg = str(e)
            line_num = 1
            # Try to extract line number from error message
            if "Line" in error_msg:
                import re
                match = re.search(r'Line (\d+)', error_msg)
                if match:
                    line_num = int(match.group(1))
            
            issues.append({
                "type": "syntax_error",
                "severity": "critical",
                "line": line_num,
                "message": f"JavaScript Syntax Error: {error_msg}",
                "suggestion": "Fix the syntax error in your JavaScript code. Check for missing semicolons, brackets, or incorrect operators."
            })
            return issues  # Return immediately
        return issues

    def _analyze_java(self, code: str) -> List[Dict]:
        """Expert SQE checks for Java."""
        issues = []
        lines = code.split('\n')
        
        # 0. SYNTAX ERROR DETECTION (Basic)
        syntax_issues = self._check_java_syntax_errors(code, lines)
        if syntax_issues:
            return syntax_issues  # Return immediately if syntax errors found
        
        for i, line in enumerate(lines, 1):
            # 1. Scanner nextInt() Bug
            if '.nextInt()' in line and i < len(lines) and '.nextLine()' in lines[i]:
                 issues.append({
                    "type": "bug",
                    "severity": "high",
                    "line": i,
                    "message": "Scanner.nextInt() followed by nextLine() detected. This is a common bug where the newline character is skipped.",
                    "suggestion": "Use sc.nextLine() and parse the integer manually, or add an extra sc.nextLine() after nextInt()."
                })

            # 2. Loop Condition Error: while(true) without break
            if 'while(true)' in line.replace(' ', ''):
                # Check for 'break' in subsequent lines (very basic check)
                found_break = False
                for delta in range(1, 20):
                    if i + delta >= len(lines): break
                    if 'break;' in lines[i+delta-1]:
                        found_break = True
                        break
                if not found_break:
                    issues.append({
                        "type": "bug",
                        "severity": "high",
                        "line": i,
                        "message": "while(true) loop detected without a clear 'break' statement within the next 20 lines.",
                        "suggestion": "Ensure the loop has a termination condition to prevent infinite execution."
                    })

            # 3. Missing parentheses in if/while
            if 'if ' in line and '(' not in line and '{' in line:
                 issues.append({
                    "type": "bug",
                    "severity": "high",
                    "line": i,
                    "message": "Syntactically incorrect 'if' statement (missing parentheses).",
                    "suggestion": "Use 'if (condition) { ... }' format."
                })

            # 4. Standard quality
            if 'System.out.println' in line:
                issues.append({
                    "type": "code_quality",
                    "severity": "low",
                    "line": i,
                    "message": "Direct use of System.out.println",
                    "suggestion": "Use a logging framework (SLF4J/Log4j)"
                })

        return issues

    def _walk_esprima(self, node):
        """Generator to walk esprima AST."""
        if hasattr(node, 'type'):
            yield node
            
            # Recursive walk for all relevant attributes
            attrs = [
                'body', 'expression', 'left', 'right', 'callee', 
                'object', 'property', 'arguments', 'declarations', 
                'init', 'test', 'consequent', 'alternate', 'params'
            ]
            for attr in attrs:
                if hasattr(node, attr):
                    val = getattr(node, attr)
                    if isinstance(val, list):
                        for child in val:
                            yield from self._walk_esprima(child)
                    elif val:
                        yield from self._walk_esprima(val)

    def _check_cpp_syntax_errors(self, code: str, lines: List[str]) -> List[Dict]:
        """Basic syntax error detection for C/C++."""
        issues = []
        
        # Check for common syntax errors
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                continue
            
            # Missing semicolon after statements (basic check)
            if stripped.startswith('using namespace') and not stripped.endswith(';'):
                issues.append({
                    "type": "syntax_error",
                    "severity": "critical",
                    "line": i,
                    "message": f"Missing semicolon at end of statement",
                    "suggestion": "Add a semicolon (;) at the end of this line."
                })
                return issues  # Return first error
            
            # Wrong operator for cout (< instead of <<)
            if 'cout' in stripped and ' < ' in stripped and '<<' not in stripped:
                issues.append({
                    "type": "syntax_error",
                    "severity": "critical",
                    "line": i,
                    "message": "Wrong operator for cout: use '<<' not '<'",
                    "suggestion": "Replace '<' with '<<' for cout operations. Example: cout << \"text\" << endl;"
                })
                return issues
            
            # Missing closing parenthesis
            open_parens = stripped.count('(')
            close_parens = stripped.count(')')
            if 'main(' in stripped and open_parens > close_parens:
                issues.append({
                    "type": "syntax_error",
                    "severity": "critical",
                    "line": i,
                    "message": "Missing closing parenthesis ')'",
                    "suggestion": "Add ')' to close the function declaration. Example: int main() {"
                })
                return issues
            
            # Comma instead of semicolon in return statement
            if 'return' in stripped and ',' in stripped and ';' not in stripped:
                issues.append({
                    "type": "syntax_error",
                    "severity": "critical",
                    "line": i,
                    "message": "Wrong punctuation: use ';' not ','",
                    "suggestion": "Replace comma with semicolon. Example: return 0;"
                })
                return issues
        
        return issues

    def _check_java_syntax_errors(self, code: str, lines: List[str]) -> List[Dict]:
        """Basic syntax error detection for Java."""
        issues = []
        
        # Check for missing semicolons
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                continue
            
            # Missing semicolon after common statements
            if any(stripped.startswith(keyword) for keyword in ['int ', 'String ', 'return ', 'System.']):
                if not stripped.endswith(';') and not stripped.endswith('{') and not stripped.endswith('('):
                    issues.append({
                        "type": "syntax_error",
                        "severity": "critical",
                        "line": i,
                        "message": "Missing semicolon at end of statement",
                        "suggestion": "Add a semicolon (;) at the end of this line."
                    })
                    return issues
            
            # Missing opening brace
            if 'class ' in stripped and '{' not in stripped:
                # Check next few lines
                found_brace = False
                for j in range(i, min(i+3, len(lines))):
                    if '{' in lines[j]:
                        found_brace = True
                        break
                if not found_brace:
                    issues.append({
                        "type": "syntax_error",
                        "severity": "critical",
                        "line": i,
                        "message": "Missing opening brace '{' for class declaration",
                        "suggestion": "Add '{' after the class name declaration."
                    })
                    return issues
        
        return issues

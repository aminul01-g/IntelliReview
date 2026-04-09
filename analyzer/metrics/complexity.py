from typing import Dict
from radon.complexity import cc_visit
from radon.metrics import mi_visit, h_visit
from ..parsers.base_parser import ParsedNode

class ComplexityAnalyzer:
    """Analyze code complexity metrics."""
    
    def analyze(self, code: str, language: str = "python") -> Dict:
        """Calculate complexity metrics."""
        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        else:
            return self._basic_metrics(code)
    
    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code complexity."""
        try:
            # Cyclomatic Complexity
            cc_results = cc_visit(code)
            
            # Maintainability Index
            mi_score = mi_visit(code, True)
            
            # Halstead Metrics
            halstead = h_visit(code)
            
            # Calculate average complexity
            avg_complexity = sum(r.complexity for r in cc_results) / len(cc_results) if cc_results else 0
            max_complexity = max((r.complexity for r in cc_results), default=0)
            
            return {
                "average_complexity": round(avg_complexity, 2),
                "max_complexity": max_complexity,
                "maintainability_index": round(mi_score, 2),
                "total_functions": len(cc_results),
                "halstead_volume": round(halstead.total.volume, 2) if halstead else 0,
                "halstead_difficulty": round(halstead.total.difficulty, 2) if halstead else 0,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code complexity (basic)."""
        return self._basic_metrics(code)
    
    def _basic_metrics(self, code: str) -> Dict:
        """Calculate basic metrics for any language."""
        lines = code.split('\n')
        loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
        
        return {
            "lines_of_code": loc,
            "total_lines": len(lines),
            "blank_lines": len([l for l in lines if not l.strip()]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
        }
from mcp.server.fastmcp import FastMCP
import os
import sys

# Ensure the root project directory is in the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from analyzer.parsers.python_parser import PythonParser
from analyzer.parsers.javascript_parser import JavaScriptParser
from analyzer.parsers.java_parser import JavaParser
from analyzer.parsers.cpp_parser import CppParser
from analyzer.metrics.complexity import ComplexityAnalyzer
from analyzer.metrics.duplication import DuplicationDetector
from analyzer.detectors.antipatterns import AntiPatternDetector
from analyzer.detectors.security import SecurityScanner
from analyzer.detectors.quality import QualityDetector
from ml_models.generators.suggestion_generator import SuggestionGenerator

mcp = FastMCP("IntelliReview")

# Initialize analyzers
parsers = {
    "python": PythonParser(),
    "javascript": JavaScriptParser(),
    "java": JavaParser(),
    "cpp": CppParser(),
    "c": CppParser(),
}

complexity_analyzer = ComplexityAnalyzer()
duplication_detector = DuplicationDetector()
antipattern_detector = AntiPatternDetector()
security_scanner = SecurityScanner()
quality_detector = QualityDetector()
suggestion_generator = SuggestionGenerator(provider="huggingface")

@mcp.tool()
async def analyze_code(code: str, language: str, filename: str = "unknown") -> str:
    """Analyze a single source code file using IntelliReview's full analysis stack.
    
    Args:
        code: The raw source code to analyze
        language: The programming language (python, javascript, java, cpp, c)
        filename: Optional filename for context
        
    Returns:
        A markdown report containing static analysis metrics and an AI review summary.
    """
    lang = language.lower()
    parser = parsers.get(lang)
    if not parser:
        return f"Error: No parser available for language '{language}'"
        
    try:
        ast = parser.parse(code, filename)
        
        metrics_data = complexity_analyzer.analyze(code, lang)
        duplicates = duplication_detector.detect(code)
        antipatterns = antipattern_detector.detect(code, ast, lang)
        security_issues = security_scanner.scan(code, filename, lang)
        quality_issues = quality_detector.detect(code, filename, lang)
        
        all_issues = antipatterns + security_issues + quality_issues
        
        # Build markdown response
        report = f"# IntelliReview Analysis for {filename} ({language})\n\n"
        report += f"**Lines of Code:** {metrics_data.get('lines_of_code', 0)}\n"
        report += f"**Complexity:** {metrics_data.get('average_complexity', 'N/A')}\n"
        report += f"**Maintainability:** {metrics_data.get('maintainability_index', 'N/A')}\n\n"
        
        report += f"## Static Issues Found ({len(all_issues)})\n"
        if not all_issues:
            report += "No issues found! ✅\n"
        else:
            for issue in all_issues[:15]: # Limit to top 15
                report += f"- **L{issue.get('line', '?')}** [{issue.get('severity', 'info').upper()}]: {issue.get('message', '')}\n"
                if "suggestion" in issue:
                    report += f"  - *Suggestion:* {issue['suggestion']}\n"
            if len(all_issues) > 15:
                report += f"- ... and {len(all_issues) - 15} more issues.\n"
        
        # Get AI review
        report += "\n## AI Executive Review\n"
        ai_summary = await suggestion_generator.generate_general_review_async(code, all_issues, lang)
        report += ai_summary
        
        return report
    except Exception as e:
        return f"Analysis failed: {str(e)}"

if __name__ == "__main__":
    mcp.run()

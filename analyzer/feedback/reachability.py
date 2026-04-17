import asyncio
import logging
from typing import Dict, Any, Optional

from api.mcp_server import check_reachability
from api.schemas.feedback_schemas import ReviewFinding

logger = logging.getLogger(__name__)

class SemanticReachabilityAnalyzer:
    """
    Performs backward AST dataflow / call-graph tracing to determine if a 
    vulnerable sink is reachable from an external entry point.
    """
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or "."

    def evaluate_reachability(self, finding: ReviewFinding) -> bool:
        """
        Evaluate if a finding's vulnerable line/function is structurally reachable.
        
        Returns:
            True if reachable or unknown (erring on the side of security).
            False if conclusively unreachable from outside (e.g. dead code or test-only).
        """
        if not finding.file_path or finding.line == 0:
            return True # Not enough context, assume reachable

        # For semantic reachability, we trace backwards from the sensitive sink
        # We need a heuristic to figure out the sink function name
        # A full AST parser could get the exact call site, but we'll use a regex approximation
        import re
        
        # If there's a dataflow trace sink, use that
        if finding.dataflow_trace:
            sink_expr = finding.dataflow_trace.sink.expression
            # try to grab function name like cursor.execute -> execute
            match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', sink_expr)
            if match:
                sink_func = match.group(1)
            else:
                sink_func = finding.dataflow_trace.sink.expression.split('.')[-1]
        else:
            # Fallback: We can't definitively trace, so assume reachable
            # (In a real implementation, we'd parse the specific line of code)
            return True

        try:
            # Run the async MCP tool logic wrap in a sync call
            report = asyncio.run(check_reachability(self.project_root, sink_func, max_depth=3))
            
            if "🟢 Reachability Verdict: **UNREACHABLE**" in report:
                return False
                
            return True
        except Exception as e:
            logger.warning(f"Reachability check failed: {e}")
            return True # Fail-safe to true

import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analyzer.detectors.security import SecurityScanner
from analyzer.detectors.quality import QualityDetector
from analyzer.detectors.ai_patterns import AIPatternDetector
from analyzer.detectors.antipatterns import AntiPatternDetector
from analyzer.pipeline.diff_review_pipeline import DiffReviewPipeline
from analyzer.scoring.delta_score import DeltaScoreEngine

def test_surgical_filter():
    print("\n--- Testing Surgical Filter ---")
    # 1. Setup Detectors
    detectors = [SecurityScanner(), QualityDetector(), AIPatternDetector(), AntiPatternDetector()]
    pipeline = DiffReviewPipeline(detectors)

    # 2. Scenario: File with 5 pre-existing bugs.
    # We change line 10: fix a bug, introduce a new one.
    # We want to see if the pipeline ignores bugs on lines 1, 2, 3, 4, 5.

    pre_code = """
def old_func():
    print("Bug 1") # Line 2
    print("Bug 2") # Line 3
    print("Bug 3") # Line 4
    print("Bug 4") # Line 5
    print("Bug 5") # Line 6

    def target(): # Line 8
        x = 10 # Line 9
        print(x) # Line 10 - THE CHANGE SITE
    """

    # We will mock a bug on line 2 (pre-existing) and line 10 (changed)
    # Since we are using real detectors, we'll use patterns they catch.

    # Pre-change: Line 2 has eval (critical), Line 10 has a simple print.
    pre_code_real = """
def setup():
    eval("import os") # Bug 1: Line 2 (Critical)
    print("Hello")    # Line 3

def target():         # Line 5
    x = 10            # Line 6
    print(x)          # Line 7 (Target line)
"""

    # Post-change: Line 2 still has eval, but Line 7 now has eval (New bug).
    post_code_real = """
def setup():
    eval("import os") # Bug 1: Line 2 (STILL HERE)
    print("Hello")    # Line 3

def target():         # Line 5
    x = 10            # Line 6
    eval("hack")      # Line 7 (NEW BUG)
"""

    # Mock Diff: Changed line 7
    # Simplified diff hunk format expected by map_diff_to_ast_context
    hunks = [
        {
            "context": ["def target():", "    x = 10"],
            "added_lines": ["    eval(\"hack\")"],
            "removed_lines": ["    print(x)"]
        }
    ]

    # We need to simulate how the mapper sees it.
    # Since the mapper uses a snippet, we'll provide the post_code and the hunks.
    # The hunk context ["def target():", "    x = 10"] starts at line 5 in the actual file
    result = pipeline.run(
        diff_hunks=hunks,
        full_code=post_code_real,
        filename="test.py",
        language="python",
        hunk_base_line=5  # Line where "def target():" appears in the actual file
    )

    print(f"Total issues found in file: {result['summary']['total_issues_found']}")
    print(f"Issues relevant to diff: {len(result['issues'])}")
    print(f"Modified scopes: {result['modified_scopes']}")

    # The bug on line 2 should be filtered out. The bug on line 7 should be kept.
    for issue in result['issues']:
        print(f"Found relevant issue at line {issue['line']}: {issue['message']}")

    assert len(result['issues']) == 1
    assert result['issues'][0]['line'] == 7
    print("✅ Surgical Filter Test Passed!")

def test_delta_score():
    print("\n--- Testing Delta Score ---")
    detectors = [SecurityScanner(), QualityDetector(), AIPatternDetector(), AntiPatternDetector()]
    engine = DeltaScoreEngine(detectors)

    # Scenario: Fix a critical bug (eval), introduce a low quality issue (console.log/print)
    # Pre: Eval on line 2
    pre_code = "def f():\n    eval('1+1')\n"
    # Post: Fixed eval, added a 'TODO' (medium/low)
    post_code = "def f():\n    print('fixed')\n    # TODO: implement better\n"

    result = engine.calculate_delta(pre_code, post_code, "test.py", "python")

    print(f"Delta Score: {result['delta_score']}")
    print(f"Resolved weight: {result['resolved_weight']}")
    print(f"Introduced weight: {result['introduced_weight']}")

    # Resolved Critical (10) - Introduced Medium/Low (2) = +8
    assert result['delta_score'] > 0
    print("✅ Delta Score Test Passed!")

if __name__ == "__main__":
    try:
        test_surgical_filter()
        test_delta_score()
        print("\nALL VERIFICATION TESTS PASSED!")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

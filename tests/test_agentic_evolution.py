import pytest
import asyncio
from pathlib import Path

from analyzer.feedback.pr_gate import PRGate, MergeReadinessVerdict
from analyzer.feedback.reachability import SemanticReachabilityAnalyzer
from api.mcp_server import get_callers
from analyzer.feedback.learning_loop import LearningLoop
from analyzer.rules.policy_engine import PolicyEngine
from api.schemas.feedback_schemas import PRReviewComment, ReviewFinding, SeverityLevel, NitSummary, DataflowTrace, DataflowNode, FindingCategory

# ─── 1. PR Gate Tests ──────────────────────────────────────────────

def test_pr_gate_pass():
    gate = PRGate(target_health_score=80.0, max_debt_hours=4.0)
    pr = PRReviewComment(
        review_id="test",
        summary="Test",
        repository="test",
        pr_number=1,
        important_findings=[],
        nit_findings=NitSummary(total_nit_count=1, shown_nits=[], collapsed_nits=[], collapse_reason=""),
        preexisting_findings=[]
    )
    verdict = gate.evaluate(pr, 100)
    
    assert verdict.can_merge is True
    assert verdict.verdict == "pass"
    assert verdict.health_score == 100.0

def test_pr_gate_block_on_health_score():
    gate = PRGate(target_health_score=80.0)
    
    # Simulate a critical finding leading to low health score
    # 1 critical finding on 10 lines of code -> 100 - (1/10)*1000 = < 80
    finding = ReviewFinding(id="1", severity=SeverityLevel.important, title="Critical Issue", narrative="", category=FindingCategory.security, file_path="test.py")
    pr = PRReviewComment(
        review_id="test",
        summary="Test",
        repository="test",
        pr_number=1,
        important_findings=[finding],
        nit_findings=None,
        preexisting_findings=[]
    )
    
    verdict = gate.evaluate(pr, 10)
    assert verdict.can_merge is False
    assert verdict.verdict == "block"
    assert "Health Score" in verdict.block_reasons[0]
    assert verdict.health_score == 0.0

def test_pr_gate_warn_on_tech_debt():
    gate = PRGate(max_debt_hours=1.0) # Low threshold
    
    # 5 preexisting findings * 15m = 75m = 1.25 hours
    findings = [ReviewFinding(id=str(i), severity=SeverityLevel.preexisting, title="", narrative="", category=FindingCategory.style, file_path="test.py") for i in range(5)]
    pr = PRReviewComment(
        review_id="test",
        summary="Test",
        repository="test",
        pr_number=1,
        important_findings=[],
        nit_findings=None,
        preexisting_findings=findings
    )
    
    verdict = gate.evaluate(pr, 100)
    assert verdict.can_merge is True
    assert verdict.verdict == "warn"
    assert verdict.technical_debt_hours > 1.0

# ─── 2. Reachability Tests ─────────────────────────────────────────

def test_semantic_reachability():
    # Since we can't easily mock the file system AST across the real codebase cleanly here without fake files,
    # we'll test the wrapper logic.
    analyzer = SemanticReachabilityAnalyzer()
    
    # 1. No file path -> defaults to reachable true
    finding_no_file = ReviewFinding(id="1", severity=SeverityLevel.important, title="", narrative="", category=FindingCategory.security, file_path="unknown.py")
    assert analyzer.evaluate_reachability(finding_no_file) is True
    
    # 2. Fake Dataflow trace sink format test
    trace = DataflowTrace(
        source=DataflowNode(line=1, expression="x", file_path="test.py", node_type="source", is_tainted=True),
        sink=DataflowNode(line=2, expression="cursor.execute(sql)", file_path="test.py", node_type="sink", is_tainted=True),
        summary="Test trace",
        transforms=[],
        is_sanitized=False
    )
    finding_with_trace = ReviewFinding(id="1", severity=SeverityLevel.important, title="", narrative="", category=FindingCategory.security, file_path="test.py", line=2, dataflow_trace=trace)
    
    # Assuming "cursor.execute" isn't magically connected to an entry point in the current working directory tests
    # If the tool can't find callers, it returns Unreachable. So we expect False here because `check_reachability` finds no callers for `execute` in our test runner working dir.
    reachable = analyzer.evaluate_reachability(finding_with_trace)
    assert reachable is False

# ─── 3. Learning Loop Tests ────────────────────────────────────────

class MockLearner:
    def __init__(self):
        self.patterns = {"sql_injection": {"total": 12}}
    def track_feedback(self, suggestion_id, issue_type, accepted, context_hash=None):
        pass
    def get_acceptance_rate(self, type_str):
        # 25% acceptance = 75% rejection (triggers > 70% threshold)
        return 0.25 

def test_learning_loop_auto_suggestion(caplog):
    loop = LearningLoop(pattern_learner=MockLearner())
    
    # Should trigger auto suggestion because total >= 10 and rejection > 0.70
    loop.on_feedback("s_123", "sql_injection", False)
    
    assert "IntelliReview Continuous Learning" in caplog.text
    assert "rejected 75%" in caplog.text
    assert "severity: ignored" in caplog.text

# ─── 4. Policy Engine Tests ────────────────────────────────────────

def test_policy_inheritance(tmp_path):
    # Setup global policy
    org_file = tmp_path / "global.yml"
    engine = PolicyEngine(str(org_file))
    
    engine.set_global_policies([
        {"id": "no-eval", "severity": "critical"} # critical is max severity
    ])
    
    # Repo tries to downgrade 'no-eval' to 'medium'
    effective = engine.get_effective_severity("no-eval", "medium")
    assert effective == "critical" # Global wins
    
    # Repo tries to elevate a non-mentioned rule
    effective_custom = engine.get_effective_severity("custom-rule", "high")
    assert effective_custom == "high"
    
    # Policy exists globally but repo specifies nothing
    assert engine.get_effective_severity("no-eval", None) == "critical"
    
    # Global policy is weak, repo makes it stricter
    engine.set_global_policies([
        {"id": "no-alert", "severity": "low"}
    ])
    effective_strict = engine.get_effective_severity("no-alert", "important")
    assert effective_strict == "important" # Stricter repo policy wins

# ─── 5. MCP get_callers Test ───────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_get_callers(tmp_path):
    # Create fake files
    f1 = tmp_path / "utils.py"
    f1.write_text("def sensitive_sink():\n    pass")
    
    f2 = tmp_path / "main.py"
    f2.write_text("from utils import sensitive_sink\n\ndef main():\n    sensitive_sink()")
    
    report = await get_callers(str(tmp_path), "sensitive_sink")
    
    assert "Callers of `sensitive_sink`" in report
    assert "main.py:L4" in report
    assert "in `main`" in report

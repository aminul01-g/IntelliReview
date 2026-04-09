
import pytest
from analyzer.metrics.complexity import ComplexityAnalyzer
from analyzer.metrics.duplication import DuplicationDetector


class TestComplexityAnalyzer:
    """Test complexity analyzer."""
    
    def test_analyze_python_code(self, sample_python_code):
        """Test analyzing Python code."""
        analyzer = ComplexityAnalyzer()
        
        metrics = analyzer.analyze(sample_python_code, "python")
        
        assert "average_complexity" in metrics
        assert "max_complexity" in metrics
        assert metrics["max_complexity"] >= 0
    
    def test_analyze_simple_code(self):
        """Test analyzing simple code."""
        analyzer = ComplexityAnalyzer()
        code = "def hello(): return 'world'"
        
        metrics = analyzer.analyze(code, "python")
        
        assert metrics["average_complexity"] == 1.0
    
    def test_basic_metrics(self):
        """Test basic metrics calculation."""
        analyzer = ComplexityAnalyzer()
        code = """
# This is a comment
def hello():
    return 'world'

# Another comment
"""
        
        metrics = analyzer._basic_metrics(code)
        
        assert "lines_of_code" in metrics
        assert "total_lines" in metrics
        assert "blank_lines" in metrics
        assert "comment_lines" in metrics


class TestDuplicationDetector:
    """Test duplication detector."""
    
    def test_detect_no_duplication(self):
        """Test code with no duplication."""
        detector = DuplicationDetector()
        code = """
def func1():
    return 1

def func2():
    return 2
"""
        
        duplicates = detector.detect(code)
        
        assert len(duplicates) == 0
    
    def test_detect_duplication(self):
        """Test code with duplication."""
        detector = DuplicationDetector()
        code = """
def func1():
    x = 1
    y = 2
    z = 3
    return x + y + z

def func2():
    x = 1
    y = 2
    z = 3
    return x + y + z
"""
        
        duplicates = detector.detect(code, min_lines=3)
        
        assert len(duplicates) > 0


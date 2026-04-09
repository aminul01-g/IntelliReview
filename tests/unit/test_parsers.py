import pytest
from analyzer.parsers.python_parser import PythonParser
from analyzer.parsers.javascript_parser import JavaScriptParser


class TestPythonParser:
    """Test Python parser."""
    
    def test_parse_simple_code(self):
        """Test parsing simple Python code."""
        parser = PythonParser()
        code = "def hello(): print('world')"
        
        ast = parser.parse(code)
        
        assert ast is not None
        assert ast.type == "Module"
    
    def test_extract_functions(self, sample_python_code):
        """Test extracting functions."""
        parser = PythonParser()
        ast = parser.parse(sample_python_code)
        
        functions = parser.extract_functions(ast)
        
        assert len(functions) >= 2
        function_names = [f.name for f in functions]
        assert "calculate_sum" in function_names
        assert "calculate_product" in function_names
    
    def test_extract_classes(self, sample_python_code):
        """Test extracting classes."""
        parser = PythonParser()
        ast = parser.parse(sample_python_code)
        
        classes = parser.extract_classes(ast)
        
        assert len(classes) == 1
        assert classes[0].name == "Calculator"
    
    def test_parse_syntax_error(self):
        """Test handling syntax errors."""
        parser = PythonParser()
        code = "def hello( print('world')"  # Missing closing parenthesis
        
        with pytest.raises(ValueError):
            parser.parse(code)


class TestJavaScriptParser:
    """Test JavaScript parser."""
    
    def test_parse_simple_code(self):
        """Test parsing simple JavaScript code."""
        parser = JavaScriptParser()
        code = "function hello() { console.log('world'); }"
        
        ast = parser.parse(code)
        
        assert ast is not None
        assert ast.type == "Program"
    
    def test_extract_functions(self, sample_javascript_code):
        """Test extracting functions."""
        parser = JavaScriptParser()
        ast = parser.parse(sample_javascript_code)
        
        functions = parser.extract_functions(ast)
        
        assert len(functions) >= 2


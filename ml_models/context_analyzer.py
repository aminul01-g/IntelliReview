from typing import Dict, List
import re

class ContextAnalyzer:
    """Analyze code context for better suggestions."""
    
    def analyze_context(self, code: str, language: str) -> Dict:
        """Analyze code context."""
        context = {
            "framework": self._detect_framework(code, language),
            "patterns": self._detect_patterns(code),
            "dependencies": self._extract_dependencies(code, language),
            "style": self._analyze_style(code, language)
        }
        
        return context
    
    def _detect_framework(self, code: str, language: str) -> str:
        """Detect the framework being used."""
        if language == "python":
            if "from flask import" in code or "import flask" in code:
                return "flask"
            elif "from django" in code or "import django" in code:
                return "django"
            elif "import fastapi" in code or "from fastapi" in code:
                return "fastapi"
        
        elif language == "javascript":
            if "import React" in code or "from 'react'" in code:
                return "react"
            elif "import Vue" in code or "from 'vue'" in code:
                return "vue"
            elif "express()" in code:
                return "express"
        
        return "unknown"
    
    def _detect_patterns(self, code: str) -> List[str]:
        """Detect design patterns in code."""
        patterns = []
        
        # Singleton pattern
        if "instance = None" in code and "__new__" in code:
            patterns.append("singleton")
        
        # Factory pattern
        if "def create_" in code or "def make_" in code:
            patterns.append("factory")
        
        # Observer pattern
        if "subscribe" in code and "notify" in code:
            patterns.append("observer")
        
        return patterns
    
    def _extract_dependencies(self, code: str, language: str) -> List[str]:
        """Extract dependencies from code."""
        dependencies = []
        
        if language == "python":
            # Extract imports
            import_lines = re.findall(r'^import\s+(\w+)', code, re.MULTILINE)
            from_imports = re.findall(r'^from\s+(\w+)', code, re.MULTILINE)
            dependencies.extend(import_lines + from_imports)
        
        elif language == "javascript":
            # Extract requires and imports
            requires = re.findall(r"require\(['\"](.+?)['\"]\)", code)
            imports = re.findall(r"from\s+['\"](.+?)['\"]", code)
            dependencies.extend(requires + imports)
        
        return list(set(dependencies))
    
    def _analyze_style(self, code: str, language: str) -> Dict:
        """Analyze coding style."""
        lines = code.split('\n')
        
        # Indentation
        indents = []
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                indents.append(indent)
        
        avg_indent = sum(indents) / len(indents) if indents else 0
        
        # Naming convention
        snake_case = len(re.findall(r'\b[a-z]+_[a-z]+\b', code))
        camel_case = len(re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b', code))
        
        return {
            "average_indentation": round(avg_indent, 1),
            "naming_convention": "snake_case" if snake_case > camel_case else "camelCase",
            "line_length": max(len(line) for line in lines) if lines else 0
        }
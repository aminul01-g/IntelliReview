"""Code analysis engine for IntelliReview."""

__all__ = []

try:
    from .parsers.python_parser import PythonParser
    __all__.append('PythonParser')
except ImportError:
    pass

try:
    from .parsers.javascript_parser import JavaScriptParser
    __all__.append('JavaScriptParser')
except ImportError:
    pass

try:
    from .parsers.java_parser import JavaParser
    __all__.append('JavaParser')
except ImportError:
    pass

try:
    from .metrics.complexity import ComplexityAnalyzer
    __all__.append('ComplexityAnalyzer')
except ImportError:
    pass

try:
    from .metrics.duplication import DuplicationDetector
    __all__.append('DuplicationDetector')
except ImportError:
    pass

try:
    from .detectors.antipatterns import AntiPatternDetector
    __all__.append('AntiPatternDetector')
except ImportError:
    pass

try:
    from .detectors.security import SecurityScanner
    __all__.append('SecurityScanner')
except ImportError:
    pass
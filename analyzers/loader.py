"""Analyzer loader for automatically selecting the right analyzer."""
import logging
from typing import Optional

from analyzers.base import ASTAnalyzer
from analyzers.python_analyzer import PythonASTAnalyzer

logger = logging.getLogger(__name__)

# Import JS analyzer if tree-sitter is available
try:
    from analyzers.javascript_analyzer import JavaScriptAnalyzer
    JS_ANALYZER_AVAILABLE = True
except ImportError:
    JS_ANALYZER_AVAILABLE = False
    logger.warning("JavaScript analyzer not available (tree-sitter not installed)")


_ANALYZERS: Optional[list[ASTAnalyzer]] = None


def load_analyzer(file_path: str) -> Optional[ASTAnalyzer]:
    """Load the appropriate analyzer for a file.

    Args:
        file_path: Path to the file to analyze

    Returns:
        Appropriate analyzer or None if no analyzer supports the file
    """
    global _ANALYZERS

    if _ANALYZERS is None:
        _ANALYZERS = _initialize_analyzers()

    for analyzer in _ANALYZERS:
        if analyzer.can_analyze(file_path):
            return analyzer

    return None


def _initialize_analyzers() -> list[ASTAnalyzer]:
    """Initialize all available analyzers."""
    analyzers: list[ASTAnalyzer] = []

    # Python analyzer (always available)
    analyzers.append(PythonASTAnalyzer())

    # JavaScript/TypeScript analyzer (if tree-sitter available)
    if JS_ANALYZER_AVAILABLE:
        try:
            analyzers.append(JavaScriptAnalyzer())
        except Exception as e:
            logger.warning(f"Failed to initialize JavaScript analyzer: {e}")

    logger.info(f"Initialized {len(analyzers)} AST analyzers")
    return analyzers

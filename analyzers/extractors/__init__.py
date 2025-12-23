"""Language-specific AST extractors."""
from analyzers.extractors.base import BaseExtractor
from analyzers.extractors.python import PythonExtractor
from analyzers.extractors.javascript import JavaScriptExtractor

# Registry of extractors by language
EXTRACTORS = {
    "python": PythonExtractor(),
    "javascript": JavaScriptExtractor(),
    "typescript": JavaScriptExtractor(),  # Reuse JS extractor for TS
    "tsx": JavaScriptExtractor(),
    "jsx": JavaScriptExtractor(),
}


def get_extractor(language: str) -> BaseExtractor:
    """Get extractor for a language.

    Args:
        language: Language name (python, javascript, etc.)

    Returns:
        Appropriate extractor instance

    Raises:
        ValueError: If language not supported
    """
    extractor = EXTRACTORS.get(language.lower())
    if not extractor:
        raise ValueError(f"No extractor available for language: {language}")
    return extractor


__all__ = ["BaseExtractor", "PythonExtractor", "JavaScriptExtractor", "get_extractor"]

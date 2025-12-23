"""Base extractor interface for language-specific AST extraction."""
from abc import ABC, abstractmethod
from tree_sitter import Node
from analyzers.base import CodeSymbol, CodeRelationship, FileAnalysisResult


class BaseExtractor(ABC):
    """Base class for language-specific AST extractors."""

    @abstractmethod
    def analyze_file(self, file_path: str, root: Node, content: str) -> FileAnalysisResult:
        """Analyze a file and extract all code intelligence.

        Args:
            file_path: Path to the file
            root: Tree-sitter AST root node
            content: Source code content

        Returns:
            Complete analysis result with symbols and relationships
        """
        pass

    def _get_text(self, node: Node) -> str:
        """Helper to get text from a node."""
        return node.text.decode("utf8") if node.text else ""

    def _extract_docstring(self, node: Node, content: str) -> str | None:
        """Extract docstring from a function/class node if present."""
        # Override in language-specific extractors
        return None


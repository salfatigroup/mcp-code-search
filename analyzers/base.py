"""Base AST analyzer interface for extracting code relationships."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CodeSymbol:
    """Represents a code symbol (function, class, method, etc.)."""
    name: str
    symbol_type: str  # "function", "class", "method", "variable", "import"
    file_path: str
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    parent_symbol: Optional[str] = None  # For methods: parent class name
    is_exported: bool = True


@dataclass
class CodeRelationship:
    """Represents a relationship between code symbols."""
    source_file: str
    source_symbol: str
    source_line: int
    target_file: Optional[str]  # None if external dependency
    target_symbol: str
    relationship_type: str  # "calls", "imports", "inherits", "instantiates"
    is_external: bool = False  # True for external/stdlib imports


@dataclass
class FileAnalysisResult:
    """Result of analyzing a single file."""
    file_path: str
    symbols: list[CodeSymbol] = field(default_factory=list)
    relationships: list[CodeRelationship] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    summary: Optional[str] = None
    error: Optional[str] = None


class ASTAnalyzer(ABC):
    """Base class for language-specific AST analyzers."""

    @abstractmethod
    def can_analyze(self, file_path: str) -> bool:
        """Check if this analyzer can handle the given file.

        Args:
            file_path: Path to the file

        Returns:
            True if this analyzer supports the file type
        """
        pass

    @abstractmethod
    def analyze(self, file_path: str, content: str) -> FileAnalysisResult:
        """Analyze a file and extract code relationships.

        Args:
            file_path: Path to the file
            content: File content as string

        Returns:
            Analysis result with symbols and relationships
        """
        pass

    def generate_file_summary(self, result: FileAnalysisResult) -> str:
        """Generate a summary of the file for semantic search.

        Args:
            result: Analysis result

        Returns:
            Human-readable summary of the file
        """
        if result.error:
            return f"Error analyzing file: {result.error}"

        parts = []

        # Module docstring or first comment
        if result.summary:
            parts.append(result.summary)

        # Key symbols
        functions = [s for s in result.symbols if s.symbol_type == "function"]
        classes = [s for s in result.symbols if s.symbol_type == "class"]

        if classes:
            parts.append(f"Defines {len(classes)} class(es): {', '.join(c.name for c in classes[:5])}")

        if functions:
            parts.append(f"Defines {len(functions)} function(s): {', '.join(f.name for f in functions[:5])}")

        # Imports
        if result.imports:
            parts.append(f"Imports: {', '.join(result.imports[:5])}")

        return " | ".join(parts) if parts else "Empty or unanalyzable file"

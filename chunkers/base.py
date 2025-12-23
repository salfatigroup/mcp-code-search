"""Base chunker interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """Represents a chunk of text from a file with AST metadata."""
    content: str
    file_path: str
    start_line: int
    end_line: int
    language: str | None  # Detected language (python, js, etc.)

    # AST metadata for enhanced search
    defined_symbols: list[str] = field(default_factory=list)      # Symbols defined in this chunk
    referenced_symbols: list[str] = field(default_factory=list)   # Symbols used in this chunk
    imports: list[str] = field(default_factory=list)              # Import statements in chunk
    calls: list[str] = field(default_factory=list)                # Function calls in chunk

    metadata: dict = field(default_factory=dict)


class BaseChunker(ABC):
    """Abstract base class for text chunkers."""

    @abstractmethod
    def chunk_file(self, file_path: str, content: str) -> list[Chunk]:
        """Split file content into chunks."""
        pass

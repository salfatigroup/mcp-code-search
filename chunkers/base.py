"""Base chunker interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a chunk of text from a file."""
    content: str
    file_path: str
    start_line: int
    end_line: int
    language: str | None  # Detected language (python, js, etc.)
    metadata: dict


class BaseChunker(ABC):
    """Abstract base class for text chunkers."""

    @abstractmethod
    def chunk_file(self, file_path: str, content: str) -> list[Chunk]:
        """Split file content into chunks."""
        pass

"""Base vector store interface."""
from abc import ABC, abstractmethod
from chunkers.base import Chunk


class BaseVectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_chunks(self, chunks: list[Chunk]) -> list[str]:
        """Add chunks with their embeddings. Returns list of IDs."""
        pass

    @abstractmethod
    def search(self, query: str, k: int = 10) -> list[dict]:
        """Search for similar chunks."""
        pass

    @abstractmethod
    def delete_by_file(self, file_path: str) -> int:
        """Delete all chunks for a file. Returns count deleted."""
        pass

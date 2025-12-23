"""Base summarizer interface."""
from abc import ABC, abstractmethod


class BaseSummarizer(ABC):
    """Abstract base class for file summarizers."""

    @abstractmethod
    def summarize_file(self, file_path: str, content: str, language: str) -> str:
        """Generate a summary of the file.

        Args:
            file_path: Path to the file
            content: File content
            language: Programming language

        Returns:
            2-3 sentence summary of the file
        """
        pass

    @abstractmethod
    def __enter__(self):
        """Load model into memory."""
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup model from memory."""
        pass

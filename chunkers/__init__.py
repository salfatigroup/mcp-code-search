"""Chunkers module for splitting text into chunks."""
from settings.config import Settings
from chunkers.base import BaseChunker, Chunk
from chunkers.code import CodeChunker

__all__ = ["BaseChunker", "Chunk", "load_chunker"]


def load_chunker(settings: Settings) -> BaseChunker:
    """Factory function to load the configured chunker."""
    return CodeChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

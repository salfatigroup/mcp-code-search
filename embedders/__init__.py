"""Embedders module for generating text embeddings."""
from settings.config import Settings
from embedders.base import BaseEmbedder
from embedders.local import LocalEmbedder

__all__ = ["BaseEmbedder", "load_embedder"]


def load_embedder(settings: Settings) -> BaseEmbedder:
    """Factory function to load the configured embedder."""
    match settings.embedder_type:
        case "local":
            return LocalEmbedder(model_name=settings.embedder_model)
        case _:
            raise ValueError(f"Unknown embedder type: {settings.embedder_type}")

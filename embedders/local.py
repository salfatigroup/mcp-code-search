"""Local embedder implementation using sentence-transformers."""
import logging
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from embedders.base import BaseEmbedder

logger = logging.getLogger(__name__)


def _detect_device() -> str:
    """Detect the best available device for inference."""
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    logger.info(f"Detected device: {device}")
    return device


class LocalEmbedder(BaseEmbedder):
    """Local embedder using HuggingFace sentence-transformers.

    Docs: https://python.langchain.com/docs/integrations/text_embedding/huggingfacehub/
    """

    def __init__(self, model_name: str = "intfloat/multilingual-e5-large-instruct"):
        logger.info(f"Loading embedding model: {model_name}")
        device = _detect_device()
        self._model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},
        )
        # Cache dimension on first embed
        self._dimension: int | None = None
        logger.info(f"Embedder initialized on device: {device}")

    @property
    def langchain_embeddings(self) -> HuggingFaceEmbeddings:
        """Return the underlying LangChain embeddings for vector store use."""
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.embed_documents(texts)
        if self._dimension is None and embeddings:
            self._dimension = len(embeddings[0])
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        embedding = self._model.embed_query(text)
        if self._dimension is None:
            self._dimension = len(embedding)
        return embedding

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Trigger dimension discovery
            self.embed_query("dimension probe")
        return self._dimension  # type: ignore

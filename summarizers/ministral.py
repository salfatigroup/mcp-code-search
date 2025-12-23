"""Ministral-3-3B for file summarization with lazy loading.

Model: https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512
Size: ~3.3B params, fits in 8GB VRAM (FP8)

Note: Ministral requires mistral-common for the tokenizer.
Install: pip install mistral-common transformers
"""
import logging
import os
import torch

logger = logging.getLogger(__name__)

# Suppress tokenizers warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    from transformers import Ministral3ForConditionalGeneration
    from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
    MINISTRAL_AVAILABLE = True
except ImportError:
    logger.warning("Ministral dependencies not available. Install: pip install transformers mistral-common")
    MINISTRAL_AVAILABLE = False

from summarizers.base import BaseSummarizer


class MinistralSummarizer(BaseSummarizer):
    """Ministral-3-3B based file summarizer with context manager for memory management."""

    def __init__(self, model_id: str = "mistralai/Ministral-3-3B-Instruct-2512"):
        if not MINISTRAL_AVAILABLE:
            raise ImportError("Ministral dependencies not installed. Run: pip install transformers mistral-common")

        self._model_id = model_id
        self._model = None
        self._tokenizer = None
        self._device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

    def __enter__(self):
        """Lazy load model only when needed."""
        if self._model is None:
            logger.info(f"Loading Ministral model: {self._model_id} on {self._device}")
            logger.info("This may take several minutes on first run (~3-6GB download)...")

            self._tokenizer = MistralTokenizer.from_pretrained(self._model_id)
            self._model = Ministral3ForConditionalGeneration.from_pretrained(
                self._model_id,
                device_map="auto",
                torch_dtype=torch.bfloat16,  # Use bfloat16 for efficiency
            )
            logger.info("Ministral model loaded successfully")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup model from memory."""
        if self._model is not None:
            logger.info("Unloading Ministral model")
            del self._model
            del self._tokenizer
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            self._model = None
            self._tokenizer = None
            logger.info("Ministral model unloaded")

    def summarize_file(self, file_path: str, content: str, language: str) -> str:
        """Generate a concise summary of the file.

        Args:
            file_path: Path to the file
            content: File content
            language: Programming language

        Returns:
            2-3 sentence summary
        """
        # Truncate content to first 2000 chars for efficiency
        truncated = content[:2000]

        prompt = f"""Summarize this {language} code file in 2-3 sentences.
Focus on: main purpose, key functions/classes, and dependencies.

File: {file_path}
Code:
{truncated}

Summary:"""

        # Encode with Mistral tokenizer
        encoded = self._tokenizer.encode_chat_completion(
            messages=[{"role": "user", "content": prompt}],
        )
        tokens = torch.tensor([encoded.tokens]).to(self._model.device)

        with torch.no_grad():
            outputs = self._model.generate(
                tokens,
                max_new_tokens=150,
                temperature=0.3,
                do_sample=True,
            )

        # Decode with Mistral tokenizer
        summary = self._tokenizer.decode(outputs[0].tolist())

        # Extract just the summary part (after "Summary:")
        if "Summary:" in summary:
            summary = summary.split("Summary:")[-1].strip()

        logger.debug(f"Generated summary for {file_path}: {summary[:100]}...")
        return summary

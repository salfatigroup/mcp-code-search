"""Language-aware code splitter using LangChain.

Docs: https://docs.langchain.com/oss/python/integrations/splitters/code_splitter
"""
import logging
from pathlib import Path
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from chunkers.base import BaseChunker, Chunk

logger = logging.getLogger(__name__)

# File extension to Language enum mapping
EXTENSION_TO_LANGUAGE: dict[str, Language] = {
    # Python
    ".py": Language.PYTHON,
    ".pyi": Language.PYTHON,
    # JavaScript/TypeScript
    ".js": Language.JS,
    ".jsx": Language.JS,
    ".ts": Language.TS,
    ".tsx": Language.TS,
    ".mjs": Language.JS,
    ".cjs": Language.JS,
    # Web
    ".html": Language.HTML,
    ".htm": Language.HTML,
    ".md": Language.MARKDOWN,
    ".mdx": Language.MARKDOWN,
    ".rst": Language.RST,
    ".latex": Language.LATEX,
    ".tex": Language.LATEX,
    # Systems
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".c": Language.C,
    ".h": Language.C,
    ".cpp": Language.CPP,
    ".hpp": Language.CPP,
    ".cc": Language.CPP,
    ".cxx": Language.CPP,
    # JVM
    ".java": Language.JAVA,
    ".kt": Language.KOTLIN,
    ".kts": Language.KOTLIN,
    ".scala": Language.SCALA,
    # Other
    ".rb": Language.RUBY,
    ".php": Language.PHP,
    ".swift": Language.SWIFT,
    ".cs": Language.CSHARP,
    ".lua": Language.LUA,
    ".pl": Language.PERL,
    ".hs": Language.HASKELL,
    ".ex": Language.ELIXIR,
    ".exs": Language.ELIXIR,
    ".sol": Language.SOL,
    ".proto": Language.PROTO,
    ".ps1": Language.POWERSHELL,
}


class CodeChunker(BaseChunker):
    """Language-aware code splitter.

    Automatically detects file type and uses appropriate separators
    for each programming language.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

        # Cache splitters by language
        self._splitters: dict[Language | None, RecursiveCharacterTextSplitter] = {}

    def _get_splitter(self, language: Language | None) -> RecursiveCharacterTextSplitter:
        """Get or create a splitter for the given language."""
        if language not in self._splitters:
            if language is not None:
                self._splitters[language] = RecursiveCharacterTextSplitter.from_language(
                    language=language,
                    chunk_size=self._chunk_size,
                    chunk_overlap=self._chunk_overlap,
                )
            else:
                # Fallback for unknown file types
                self._splitters[None] = RecursiveCharacterTextSplitter(
                    chunk_size=self._chunk_size,
                    chunk_overlap=self._chunk_overlap,
                    separators=["\n\n", "\n", " ", ""],
                )
        return self._splitters[language]

    def detect_language(self, file_path: str) -> Language | None:
        """Detect language from file extension."""
        ext = Path(file_path).suffix.lower()
        return EXTENSION_TO_LANGUAGE.get(ext)

    def chunk_file(self, file_path: str, content: str) -> list[Chunk]:
        """Split file into language-aware chunks."""
        language = self.detect_language(file_path)
        splitter = self._get_splitter(language)

        logger.debug(f"Chunking {file_path} (language: {language.value if language else 'unknown'})")

        docs = splitter.create_documents(
            [content],
            metadatas=[{"file_path": file_path}]
        )

        chunks = []
        for doc in docs:
            # Calculate line numbers
            start_idx = content.find(doc.page_content)
            start_line = content[:start_idx].count("\n") + 1 if start_idx >= 0 else 1
            end_line = start_line + doc.page_content.count("\n")

            chunks.append(Chunk(
                content=doc.page_content,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                language=language.value if language else None,
                metadata=doc.metadata,
            ))

        logger.info(f"Split {file_path} into {len(chunks)} chunks")
        return chunks

"""Tree-sitter based AST analyzer for multi-language support.

Uses tree-sitter-language-pack for 160+ languages.
Docs: https://tree-sitter.github.io/tree-sitter/using-parsers/
"""
import logging
from pathlib import Path
from tree_sitter import Parser, Node
from tree_sitter_language_pack import get_parser
from analyzers.base import ASTAnalyzer, FileAnalysisResult
from analyzers.extractors import get_extractor

logger = logging.getLogger(__name__)

# Map file extensions to tree-sitter language names
EXTENSION_TO_TREE_SITTER = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "c_sharp",
}


class TreeSitterAnalyzer(ASTAnalyzer):
    """Multi-language AST analyzer using Tree-sitter."""

    def __init__(self):
        # Language parsers cached by language name
        self._parsers: dict[str, Parser] = {}
        logger.info("TreeSitterAnalyzer initialized")

    def can_analyze(self, file_path: str) -> bool:
        """Check if we can analyze this file type."""
        ext = Path(file_path).suffix.lower()
        return ext in EXTENSION_TO_TREE_SITTER

    def _get_language_name(self, file_path: str) -> str | None:
        """Get tree-sitter language name from file extension."""
        ext = Path(file_path).suffix.lower()
        return EXTENSION_TO_TREE_SITTER.get(ext)

    def _get_parser(self, language_name: str) -> Parser:
        """Get or create parser for language."""
        if language_name not in self._parsers:
            logger.debug(f"Loading Tree-sitter parser for {language_name}")
            parser = get_parser(language_name)
            self._parsers[language_name] = parser
            logger.debug(f"Parser loaded for {language_name}")
        return self._parsers[language_name]

    def parse(self, content: str, language: str) -> Node | None:
        """Parse content and return AST root node."""
        try:
            parser = self._get_parser(language)
            tree = parser.parse(bytes(content, "utf8"))
            return tree.root_node
        except Exception as e:
            logger.warning(f"Failed to parse {language} code: {e}")
            return None

    def analyze(self, file_path: str, content: str) -> FileAnalysisResult:
        """Analyze a file and extract all code intelligence."""
        language = self._get_language_name(file_path)

        if not language:
            return FileAnalysisResult(
                file_path=file_path,
                error=f"Unsupported file type: {Path(file_path).suffix}"
            )

        root = self.parse(content, language)
        if not root:
            return FileAnalysisResult(
                file_path=file_path,
                error=f"Failed to parse {language} code"
            )

        try:
            extractor = get_extractor(language)
            result = extractor.analyze_file(file_path, root, content)
            logger.info(f"Analyzed {file_path}: {len(result.symbols)} symbols, {len(result.relationships)} relationships")
            return result
        except Exception as e:
            logger.error(f"Analysis failed for {file_path}: {e}", exc_info=True)
            return FileAnalysisResult(
                file_path=file_path,
                error=str(e)
            )


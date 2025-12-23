"""Simple rule-based file summarizer - no model dependencies required."""
import logging
from summarizers.base import BaseSummarizer

logger = logging.getLogger(__name__)


class SimpleSummarizer(BaseSummarizer):
    """Rule-based file summarizer using AST metadata and heuristics.

    Generates summaries from:
    - Module docstrings
    - Function/class names
    - Import statements
    - File structure

    No model loading required - instant and memory-efficient.
    """

    def __init__(self):
        logger.info("SimpleSummarizer initialized (no model loading required)")

    def __enter__(self):
        """No model to load."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """No cleanup needed."""
        pass

    def summarize_file(self, file_path: str, content: str, language: str) -> str:
        """Generate a summary from code structure.

        Args:
            file_path: Path to the file
            content: File content
            language: Programming language

        Returns:
            Summary based on code structure
        """
        lines = content.split('\n')
        summary_parts = []

        # Extract module docstring (first few lines)
        docstring = self._extract_module_docstring(lines, language)
        if docstring:
            summary_parts.append(docstring)

        # Extract key information
        functions = self._count_definitions(content, language, "function")
        classes = self._count_definitions(content, language, "class")
        imports = self._extract_imports(lines, language)

        # Build summary
        if classes > 0:
            summary_parts.append(f"Defines {classes} class(es)")
        if functions > 0:
            summary_parts.append(f"Contains {functions} function(s)")
        if imports:
            summary_parts.append(f"Imports: {', '.join(imports[:5])}")

        if not summary_parts:
            return f"{language.capitalize()} module"

        summary = ". ".join(summary_parts)
        logger.debug(f"Generated summary for {file_path}: {summary[:100]}")
        return summary

    def _extract_module_docstring(self, lines: list[str], language: str) -> str | None:
        """Extract module-level docstring."""
        if language == "python":
            # Look for triple-quoted strings at the top
            for i, line in enumerate(lines[:10]):
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    # Find closing quote
                    quote = '"""' if stripped.startswith('"""') else "'''"
                    docstring_lines = [stripped.replace(quote, '')]
                    for j in range(i + 1, min(i + 20, len(lines))):
                        if quote in lines[j]:
                            docstring_lines.append(lines[j].split(quote)[0])
                            break
                        docstring_lines.append(lines[j])
                    return ' '.join(docstring_lines).strip()[:200]

        elif language in ("javascript", "typescript"):
            # Look for /** */ comments at the top
            in_comment = False
            comment_lines = []
            for line in lines[:20]:
                stripped = line.strip()
                if stripped.startswith('/**'):
                    in_comment = True
                if in_comment:
                    comment_lines.append(stripped.replace('/**', '').replace('*/', '').replace('*', '').strip())
                if '*/' in stripped:
                    break
            if comment_lines:
                return ' '.join(comment_lines).strip()[:200]

        return None

    def _count_definitions(self, content: str, language: str, def_type: str) -> int:
        """Count function or class definitions."""
        if language == "python":
            if def_type == "function":
                return content.count('\ndef ') + content.count('\nasync def ')
            elif def_type == "class":
                return content.count('\nclass ')

        elif language in ("javascript", "typescript"):
            if def_type == "function":
                count = content.count('function ') + content.count('async function ')
                count += content.count('=>')  # Arrow functions
                return count
            elif def_type == "class":
                return content.count('class ')

        return 0

    def _extract_imports(self, lines: list[str], language: str) -> list[str]:
        """Extract import statements."""
        imports = []

        if language == "python":
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('import '):
                    imports.append(stripped.split()[1].split('.')[0])
                elif stripped.startswith('from '):
                    parts = stripped.split()
                    if len(parts) > 1:
                        imports.append(parts[1].split('.')[0])

        elif language in ("javascript", "typescript"):
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('import ') and ' from ' in stripped:
                    # import X from 'module'
                    module = stripped.split(' from ')[-1].strip().strip("';\"")
                    imports.append(module)
                elif 'require(' in stripped:
                    # const X = require('module')
                    start = stripped.find("require('") or stripped.find('require("')
                    if start >= 0:
                        module = stripped[start+9:].split("'")[0].split('"')[0]
                        imports.append(module)

        return list(set(imports))[:10]  # Unique, max 10

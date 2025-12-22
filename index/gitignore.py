"""Gitignore-aware file filtering using pathspec.

Docs: https://github.com/cpburnz/python-pathspec
"""
import logging
from pathlib import Path
import pathspec

logger = logging.getLogger(__name__)


class GitignoreFilter:
    """Filter files based on .gitignore rules.

    Reads .gitignore from project root and provides methods to check
    if files should be ignored.
    """

    def __init__(self, project_root: str):
        self._root = Path(project_root)
        self._spec: pathspec.GitIgnoreSpec | None = None
        self._load_gitignore()

    def _load_gitignore(self) -> None:
        """Load and parse .gitignore file."""
        gitignore_path = self._root / ".gitignore"

        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                patterns = f.read().splitlines()
            # GitIgnoreSpec handles gitignore-specific behavior
            self._spec = pathspec.GitIgnoreSpec.from_lines(patterns)
            logger.info(f"Loaded {len(patterns)} patterns from .gitignore")
        else:
            logger.info("No .gitignore found")
            self._spec = None

    def reload(self) -> None:
        """Reload .gitignore (call when file changes)."""
        self._load_gitignore()

    def is_ignored(self, file_path: str) -> bool:
        """Check if a file path should be ignored.

        Args:
            file_path: Path relative to project root

        Returns:
            True if file matches a gitignore pattern
        """
        if self._spec is None:
            return False

        # pathspec expects forward slashes
        normalized = file_path.replace("\\", "/")
        return self._spec.match_file(normalized)

    def filter_paths(self, paths: list[str]) -> list[str]:
        """Filter a list of paths, removing ignored ones.

        Args:
            paths: List of paths relative to project root

        Returns:
            List of paths that are NOT ignored
        """
        if self._spec is None:
            return paths

        return [p for p in paths if not self.is_ignored(p)]

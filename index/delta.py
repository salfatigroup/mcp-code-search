"""Git delta detection for incremental indexing."""
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FileChange:
    """Represents a file change detected by git."""
    path: str
    status: str  # "added", "modified", "deleted"


def get_git_delta(project_root: str, since_commit: str | None = None) -> list[FileChange]:
    """Get changed files using git.

    Note: git ls-files only returns TRACKED files (committed to git).
    Untracked files will not appear until they are added and committed.
    """
    root = Path(project_root)

    if since_commit:
        cmd = ["git", "diff", "--name-status", since_commit, "HEAD"]
        logger.debug(f"Getting changed files since commit: {since_commit}")
    else:
        cmd = ["git", "ls-files"]
        logger.debug(f"Getting all tracked files in {root}")

    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"Git command failed: {result.stderr}")
        return []

    changes = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        if since_commit:
            status, path = line.split("\t", 1)
            status_map = {"A": "added", "M": "modified", "D": "deleted"}
            changes.append(FileChange(path=path, status=status_map.get(status, "modified")))
        else:
            changes.append(FileChange(path=line, status="added"))

    logger.debug(f"Git returned {len(changes)} files")
    if len(changes) == 0:
        logger.warning(
            "No tracked files found. Note: git ls-files only returns files "
            "that have been committed. Run 'git add .' and 'git commit' first."
        )

    return changes


def get_current_commit(project_root: str) -> str | None:
    """Get current HEAD commit hash."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None

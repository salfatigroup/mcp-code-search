"""File discovery for indexing - scans filesystem directly."""
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FileChange:
    """Represents a file change detected."""
    path: str
    status: str  # "added", "modified", "deleted"


def get_all_files(project_root: str) -> list[FileChange]:
    """Get all files in the project by walking the directory tree.

    This scans the actual filesystem, not just git-tracked files.
    The gitignore filter will be applied separately by the worker.
    """
    root = Path(project_root).resolve()
    logger.debug(f"Scanning all files in {root}")

    changes = []
    for file_path in root.rglob("*"):
        # Skip directories
        if file_path.is_dir():
            continue

        # Get relative path
        try:
            rel_path = file_path.relative_to(root)
            changes.append(FileChange(
                path=str(rel_path),
                status="added"
            ))
        except ValueError:
            # File is outside project root
            continue

    logger.info(f"Found {len(changes)} total files in {root}")
    return changes


def get_git_delta(project_root: str, since_commit: str | None = None) -> list[FileChange]:
    """Get changed files using git diff (for incremental updates).

    Only used for incremental indexing to detect what changed since last run.
    For full indexing, use get_all_files() instead.
    """
    root = Path(project_root)

    if since_commit:
        cmd = ["git", "diff", "--name-status", since_commit, "HEAD"]
        logger.debug(f"Getting changed files since commit: {since_commit}")
    else:
        # For full index, scan filesystem directly
        logger.debug(f"Full index requested, using filesystem scan")
        return get_all_files(project_root)

    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)

    if result.returncode != 0:
        logger.warning(f"Git diff failed, falling back to full scan: {result.stderr}")
        return get_all_files(project_root)

    changes = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        status, path = line.split("\t", 1)
        status_map = {"A": "added", "M": "modified", "D": "deleted"}
        changes.append(FileChange(path=path, status=status_map.get(status, "modified")))

    logger.debug(f"Git diff returned {len(changes)} changed files")
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

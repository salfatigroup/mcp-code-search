"""Background indexing worker with gitignore support.

Runs periodic indexing cycles, detecting file changes via git delta
and respecting .gitignore patterns.
"""
import asyncio
import logging
from pathlib import Path
from index.manager import IndexManager
from index.delta import get_git_delta, get_current_commit
from index.gitignore import GitignoreFilter
from chunkers.code import EXTENSION_TO_LANGUAGE
from settings.config import Settings

logger = logging.getLogger(__name__)


class IndexWorker:
    """Background worker for continuous indexing."""

    def __init__(self, settings: Settings, index_manager: IndexManager, chunker):
        self._settings = settings
        self._index_manager = index_manager
        self._chunker = chunker  # Need chunker for language detection
        self._gitignore = GitignoreFilter(settings.project_root)
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_commit: str | None = None

        # Build set of indexable extensions from chunker's language map + settings
        self._indexable_extensions = set(EXTENSION_TO_LANGUAGE.keys())
        self._indexable_extensions.update(self._settings.file_extensions)

        logger.info(f"IndexWorker initialized with {len(self._indexable_extensions)} supported extensions")
        logger.debug(f"Supported extensions: {sorted(self._indexable_extensions)}")
        logger.debug(f"Ignore patterns: {self._settings.ignore_patterns}")

    def _should_index(self, file_path: str) -> bool:
        """Check if file should be indexed.

        Checks:
        1. File extension is supported
        2. File is not in .gitignore
        3. File is not in settings ignore_patterns
        """
        path = Path(file_path)

        # Check extension is supported
        if path.suffix.lower() not in self._indexable_extensions:
            logger.debug(f"Skipping {file_path}: unsupported extension '{path.suffix}'")
            return False

        # Check .gitignore
        if self._gitignore.is_ignored(file_path):
            logger.debug(f"Skipping {file_path}: matched .gitignore pattern")
            return False

        # Check settings ignore patterns (for additional ignores)
        for pattern in self._settings.ignore_patterns:
            if pattern in file_path:
                logger.debug(f"Skipping {file_path}: matched ignore pattern '{pattern}'")
                return False

        logger.debug(f"Will index: {file_path}")
        return True

    async def _index_loop(self) -> None:
        """Main indexing loop."""
        # Initial full index on startup
        logger.info("Starting initial index...")
        await self._run_index_cycle(full=True)

        while self._running:
            await asyncio.sleep(self._settings.index_interval)

            try:
                # Reload gitignore in case it changed
                self._gitignore.reload()
                await self._run_index_cycle(full=False)
            except Exception as e:
                logger.error(f"Index cycle failed: {e}")

    async def _run_index_cycle(self, full: bool = False) -> None:
        """Run a single indexing cycle.

        Args:
            full: If True, index all files. If False, only changed files.
        """
        cycle_type = "full" if full else "incremental"
        logger.info(f"Starting {cycle_type} index cycle (last_commit={self._last_commit})")

        if full:
            changes = get_git_delta(self._settings.project_root, since_commit=None)
        else:
            changes = get_git_delta(
                self._settings.project_root,
                since_commit=self._last_commit
            )

        logger.info(f"Found {len(changes)} changed files from git")

        indexed = 0
        deleted = 0
        skipped = 0
        failed = 0
        files_to_summarize = []

        for change in changes:
            logger.debug(f"Processing change: {change.path} (status={change.status})")

            if change.status == "deleted":
                # Remove from index
                logger.debug(f"Deleting {change.path}")
                await asyncio.to_thread(
                    self._index_manager.delete_file,
                    change.path
                )
                deleted += 1
                continue

            if not self._should_index(change.path):
                skipped += 1
                continue

            # Index file (CPU-bound, run in thread pool)
            logger.debug(f"Indexing {change.path}...")
            success = await asyncio.to_thread(
                self._index_manager.index_file,
                change.path
            )
            if success:
                indexed += 1

                # Collect for batch summarization
                if self._settings.enable_summaries:
                    try:
                        full_path = Path(self._settings.project_root) / change.path
                        content = full_path.read_text(encoding="utf-8")
                        language = self._chunker.detect_language(change.path)
                        if language:
                            files_to_summarize.append((change.path, content, language.value))
                            logger.debug(f"Collected {change.path} for summarization")
                        else:
                            logger.debug(f"No language detected for {change.path}, skipping summary")
                    except Exception as e:
                        logger.warning(f"Could not prepare {change.path} for summarization: {e}")
                else:
                    logger.debug(f"Summaries disabled, skipping {change.path}")
            else:
                failed += 1

        # Batch summarize files (model loaded once)
        logger.info(f"Collected {len(files_to_summarize)} files for summarization (enable_summaries={self._settings.enable_summaries})")
        if files_to_summarize:
            logger.info(f"Batch summarizing {len(files_to_summarize)} files...")
            await asyncio.to_thread(
                self._index_manager.batch_summarize_files,
                files_to_summarize
            )
        else:
            logger.warning("No files collected for summarization")

        # Update last commit for next delta
        new_commit = get_current_commit(self._settings.project_root)
        logger.debug(f"Updating last_commit: {self._last_commit} -> {new_commit}")
        self._last_commit = new_commit

        logger.info(f"Index cycle complete: {indexed} indexed, {deleted} deleted, {skipped} skipped, {failed} failed")

    async def start(self) -> None:
        """Start the background worker."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._index_loop())
        logger.info("Index worker started")

    async def stop(self) -> None:
        """Stop the background worker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Index worker stopped")

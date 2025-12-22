"""Index manager for orchestrating the indexing process."""
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from db.connection import DatabaseManager
from db.models import IndexedFile, IndexStatus
from db.vectorstore.base import BaseVectorStore
from chunkers.base import BaseChunker
from embedders.base import BaseEmbedder
from settings.config import Settings

logger = logging.getLogger(__name__)


class IndexManager:
    """Orchestrates the indexing process."""

    def __init__(
        self,
        settings: Settings,
        db: DatabaseManager,
        vectorstore: BaseVectorStore,
        chunker: BaseChunker,
        embedder: BaseEmbedder,
    ):
        self._settings = settings
        self._db = db
        self._vectorstore = vectorstore
        self._chunker = chunker
        self._embedder = embedder

    def index_file(self, file_path: str) -> bool:
        """Index a single file. Returns True on success."""
        full_path = Path(self._settings.project_root) / file_path

        if not full_path.exists():
            logger.warning(f"File not found: {file_path}")
            return False

        logger.debug(f"Indexing file: {file_path}")

        with self._db.session() as session:
            # Get or create record
            record = session.query(IndexedFile).filter_by(file_path=file_path).first()
            if not record:
                record = IndexedFile(file_path=file_path, file_hash="")
                session.add(record)
                logger.debug(f"Created new index record for {file_path}")

            try:
                content = full_path.read_text(encoding="utf-8")
                content_hash = hashlib.sha256(content.encode()).hexdigest()

                # Skip if unchanged
                if record.file_hash == content_hash and record.status == IndexStatus.COMPLETED:
                    logger.debug(f"File unchanged, skipping: {file_path}")
                    return True

                record.status = IndexStatus.IN_PROGRESS
                session.commit()

                # Delete old chunks
                deleted_count = self._vectorstore.delete_by_file(file_path)
                if deleted_count > 0:
                    logger.debug(f"Deleted {deleted_count} old chunks for {file_path}")

                # Chunk and add to vector store
                chunks = self._chunker.chunk_file(file_path, content)
                self._vectorstore.add_chunks(chunks)

                # Update record
                record.file_hash = content_hash
                record.status = IndexStatus.COMPLETED
                record.chunk_count = len(chunks)
                record.error_message = None
                record.indexed_at = datetime.utcnow()

                logger.info(f"Successfully indexed {file_path} ({len(chunks)} chunks)")
                return True

            except Exception as e:
                logger.error(f"Failed to index {file_path}: {e}")
                record.status = IndexStatus.FAILED
                record.error_message = str(e)
                return False

    def delete_file(self, file_path: str) -> bool:
        """Remove a file from the index. Returns True on success."""
        logger.debug(f"Deleting file from index: {file_path}")

        with self._db.session() as session:
            # Delete from vector store
            deleted_count = self._vectorstore.delete_by_file(file_path)

            # Delete from tracking database
            record = session.query(IndexedFile).filter_by(file_path=file_path).first()
            if record:
                session.delete(record)
                logger.info(f"Removed {file_path} from index ({deleted_count} chunks)")

        return True

    def get_status(self, compact: bool = True) -> dict:
        """Get indexing status."""
        with self._db.session() as session:
            files = session.query(IndexedFile).all()

            if compact:
                by_status = {}
                for f in files:
                    by_status.setdefault(f.status.value, 0)
                    by_status[f.status.value] += 1
                return {"total": len(files), "by_status": by_status}

            return {
                "total": len(files),
                "files": [
                    {
                        "path": f.file_path,
                        "status": f.status.value,
                        "chunks": f.chunk_count,
                        "error": f.error_message,
                    }
                    for f in files
                ]
            }

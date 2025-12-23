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
        summarizer=None,  # Optional: for file summaries
        analyzer=None,    # Optional: for AST analysis
        summary_store=None,  # Optional: file summary vector store
    ):
        self._settings = settings
        self._db = db
        self._vectorstore = vectorstore
        self._chunker = chunker
        self._embedder = embedder
        self._summarizer = summarizer
        self._analyzer = analyzer
        self._summary_store = summary_store

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

                # NEW: Extract AST information if enabled
                if self._settings.enable_ast and self._analyzer:
                    file_size = len(content)
                    if file_size <= self._settings.ast_max_file_size:
                        try:
                            result = self._analyzer.analyze(file_path, content)
                            if not result.error:
                                self._store_ast_data(file_path, result)
                        except Exception as e:
                            logger.warning(f"AST extraction failed for {file_path}: {e}")

                logger.info(f"Successfully indexed {file_path} ({len(chunks)} chunks)")
                return True

            except Exception as e:
                logger.error(f"Failed to index {file_path}: {e}", exc_info=True)
                record.status = IndexStatus.FAILED
                record.error_message = str(e)
                return False

    def batch_summarize_files(self, files: list[tuple[str, str, str]]) -> None:
        """Batch summarize multiple files with one model load.

        Args:
            files: List of (file_path, content, language) tuples
        """
        if not self._settings.enable_summaries or not self._summarizer or not self._summary_store:
            return

        logger.info(f"Batch summarizing {len(files)} files")

        with self._summarizer:  # Load model ONCE
            for file_path, content, language in files:
                try:
                    summary = self._summarizer.summarize_file(file_path, content, language)
                    self._store_file_summary(file_path, summary, language, len(content.splitlines()))
                except Exception as e:
                    logger.error(f"Failed to summarize {file_path}: {e}")

    def _store_file_summary(self, file_path: str, summary: str, language: str, loc: int) -> None:
        """Store file summary in database and vector store."""
        from db.models import FileSummary

        with self._db.session() as session:
            # Store in database
            file_summary = session.query(FileSummary).filter_by(file_path=file_path).first()
            if not file_summary:
                file_summary = FileSummary(file_path=file_path, file_hash="", summary=summary, language=language, loc=loc)
                session.add(file_summary)
            else:
                file_summary.summary = summary
                file_summary.language = language
                file_summary.loc = loc

        # Store in vector store
        if self._summary_store:
            self._summary_store.add_summary(file_path, summary)
            logger.debug(f"Stored summary for {file_path}")

    def _store_ast_data(self, file_path: str, result) -> None:
        """Store AST analysis results in database."""
        from db.models import Symbol, CodeRelationship

        with self._db.session() as session:
            # Delete old data
            session.query(Symbol).filter_by(file_path=file_path).delete()
            session.query(CodeRelationship).filter_by(source_file=file_path).delete()

            # Add symbols
            for sym in result.symbols:
                session.add(Symbol(
                    file_path=file_path,
                    symbol_name=sym.name,
                    symbol_type=sym.symbol_type,
                    line_start=sym.line_start,
                    line_end=sym.line_end,
                    parent_symbol=sym.parent_symbol,
                    signature=sym.signature,
                    docstring=sym.docstring,
                    is_exported=sym.is_exported
                ))

            # Add relationships
            for rel in result.relationships:
                session.add(CodeRelationship(
                    source_file=rel.source_file,
                    source_symbol=rel.source_symbol,
                    source_line=rel.source_line,
                    target_file=rel.target_file,
                    target_symbol=rel.target_symbol,
                    relationship_type=rel.relationship_type,
                    is_external=rel.is_external
                ))

        logger.info(f"Stored {len(result.symbols)} symbols and {len(result.relationships)} relationships for {file_path}")

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

"""SQLite-vec vector store implementation using LangChain.

Docs: https://docs.langchain.com/oss/python/integrations/vectorstores/sqlitevec/
"""
import logging
from pathlib import Path
from langchain_community.vectorstores import SQLiteVec
from db.vectorstore.base import BaseVectorStore
from chunkers.base import Chunk
from embedders.base import BaseEmbedder

logger = logging.getLogger(__name__)


class SQLiteVectorStore(BaseVectorStore):
    """SQLite-vec based vector store using LangChain integration.

    Note: SQLiteVec doesn't support delete/update yet, so we track file->rowid
    mappings in a separate table and recreate on file changes.
    """

    def __init__(self, db_path: str, embedder: BaseEmbedder, table: str = "chunks"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._table = table
        self._embedder = embedder

        logger.info(f"Initializing SQLiteVec at {db_path}")
        # Create connection for SQLiteVec with thread safety disabled for asyncio
        import sqlite3
        import sqlite_vec

        self._connection = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False  # Required for asyncio.to_thread
        )
        # Set row_factory so fetchone() returns dict-like objects
        self._connection.row_factory = sqlite3.Row

        # Load sqlite-vec extension
        logger.debug("Loading sqlite-vec extension")
        self._connection.enable_load_extension(True)
        sqlite_vec.load(self._connection)
        self._connection.enable_load_extension(False)
        logger.debug("sqlite-vec extension loaded")

        # Initialize vector store with LangChain embeddings
        self._store = SQLiteVec(
            table=table,
            db_file=str(self._db_path),
            embedding=embedder.langchain_embeddings,
            connection=self._connection,
        )

        # Create file tracking table (for deletion workaround)
        self._init_tracking_table()
        logger.info("Vector store initialized")

    def _init_tracking_table(self) -> None:
        """Create table to track which rowids belong to which files."""
        cursor = self._connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunk_file_map (
                rowid INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON chunk_file_map(file_path)")
        self._connection.commit()

    def add_chunks(self, chunks: list[Chunk]) -> list[str]:
        """Add chunks to the vector store. Returns list of IDs."""
        if not chunks:
            return []

        logger.debug(f"Adding {len(chunks)} chunks from {chunks[0].file_path}")

        try:
            texts = [c.content for c in chunks]
            metadatas = [
                {
                    "file_path": c.file_path,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "language": c.language,
                }
                for c in chunks
            ]

            logger.debug(f"Calling add_texts with {len(texts)} texts")
            # Add via LangChain's add_texts (handles embedding internally)
            ids = self._store.add_texts(texts=texts, metadatas=metadatas)
            logger.debug(f"add_texts returned: {ids} (type: {type(ids)})")
            logger.info(f"Added {len(ids) if isinstance(ids, list) else 'unknown'} chunks to vector store")

            # Track file->rowid mappings for deletion
            if chunks and ids:
                cursor = self._connection.cursor()
                file_path = chunks[0].file_path
                # Handle different return types from add_texts
                if isinstance(ids, list):
                    for id_ in ids:
                        cursor.execute(
                            "INSERT OR REPLACE INTO chunk_file_map (rowid, file_path) VALUES (?, ?)",
                            (int(id_), file_path)
                        )
                self._connection.commit()

            return ids if isinstance(ids, list) else []

        except Exception as e:
            logger.error(f"Error in add_chunks: {e}", exc_info=True)
            raise

    def search(self, query: str, k: int = 10) -> list[dict]:
        """Search for similar chunks using text query."""
        logger.debug(f"Searching for: '{query}' (limit={k})")
        results = self._store.similarity_search(query, k=k)
        logger.info(f"Found {len(results)} results for query")
        return [
            {
                "content": doc.page_content,
                "file_path": doc.metadata.get("file_path"),
                "start_line": doc.metadata.get("start_line"),
                "end_line": doc.metadata.get("end_line"),
            }
            for doc in results
        ]

    def delete_by_file(self, file_path: str) -> int:
        """Delete all chunks for a file. Returns count deleted.

        Note: Since SQLiteVec doesn't have delete API, we directly delete
        from the underlying vec0 table using rowids tracked in chunk_file_map.
        """
        cursor = self._connection.cursor()

        # Get rowids for this file
        cursor.execute("SELECT rowid FROM chunk_file_map WHERE file_path = ?", (file_path,))
        rowids = [row[0] for row in cursor.fetchall()]

        if not rowids:
            logger.debug(f"No chunks found to delete for {file_path}")
            return 0

        # Delete from vec0 table (SQLiteVec's underlying table)
        placeholders = ",".join("?" * len(rowids))
        cursor.execute(f"DELETE FROM {self._table} WHERE rowid IN ({placeholders})", rowids)

        # Delete from tracking table
        cursor.execute("DELETE FROM chunk_file_map WHERE file_path = ?", (file_path,))
        self._connection.commit()

        logger.info(f"Deleted {len(rowids)} chunks for {file_path}")
        return len(rowids)

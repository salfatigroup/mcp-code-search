"""File summaries vector store for semantic file search."""
import logging
import sqlite3
from pathlib import Path
from langchain_community.vectorstores import SQLiteVec
from embedders.base import BaseEmbedder

logger = logging.getLogger(__name__)


class FileSummaryVectorStore:
    """Vector store for file summaries to enable semantic file search."""

    def __init__(self, db_path: str, embedder: BaseEmbedder, table: str = "file_summaries_vec"):
        self._db_path = Path(db_path)
        self._table = table
        self._embedder = embedder

        logger.info(f"Initializing FileSummaryVectorStore at {db_path}")

        # Create connection with thread safety disabled
        import sqlite_vec
        self._connection = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False
        )
        self._connection.row_factory = sqlite3.Row

        # Load sqlite-vec extension
        self._connection.enable_load_extension(True)
        sqlite_vec.load(self._connection)
        self._connection.enable_load_extension(False)

        # Initialize vector store
        self._store = SQLiteVec(
            table=table,
            db_file=str(self._db_path),
            embedding=embedder.langchain_embeddings,
            connection=self._connection,
        )

        # Create tracking table
        self._init_tracking_table()
        logger.info("File summary vector store initialized")

    def _init_tracking_table(self) -> None:
        """Create table to track file summary vector IDs."""
        cursor = self._connection.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._table}_map (
                rowid INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL UNIQUE
            )
        """)
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self._table}_file ON {self._table}_map(file_path)")
        self._connection.commit()

    def add_summary(self, file_path: str, summary: str) -> str | None:
        """Add or update file summary in vector store.

        Args:
            file_path: Path to the file
            summary: File summary text

        Returns:
            ID of the added summary
        """
        logger.debug(f"Adding summary for {file_path}")

        # Delete existing summary if present
        self.delete_summary(file_path)

        # Add new summary
        try:
            ids = self._store.add_texts(
                texts=[summary],
                metadatas=[{"file_path": file_path}]
            )

            if ids:
                cursor = self._connection.cursor()
                cursor.execute(
                    f"INSERT OR REPLACE INTO {self._table}_map (rowid, file_path) VALUES (?, ?)",
                    (int(ids[0]), file_path)
                )
                self._connection.commit()
                logger.info(f"Added file summary for {file_path}")
                return ids[0]

        except Exception as e:
            logger.error(f"Failed to add summary for {file_path}: {e}", exc_info=True)
            return None

    def search(self, query: str, k: int = 20) -> list[dict]:
        """Search file summaries semantically.

        Args:
            query: Semantic search query
            k: Number of results

        Returns:
            List of files with paths and summaries
        """
        logger.debug(f"Searching file summaries: '{query}' (limit={k})")
        results = self._store.similarity_search(query, k=k)

        return [
            {
                "file_path": doc.metadata.get("file_path"),
                "summary": doc.page_content,
            }
            for doc in results
        ]

    def delete_summary(self, file_path: str) -> int:
        """Delete file summary from vector store.

        Args:
            file_path: Path to the file

        Returns:
            Number of summaries deleted
        """
        cursor = self._connection.cursor()

        # Get rowid
        cursor.execute(f"SELECT rowid FROM {self._table}_map WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()

        if not row:
            return 0

        rowid = row[0]

        # Delete from vector table
        cursor.execute(f"DELETE FROM {self._table} WHERE rowid = ?", (rowid,))

        # Delete from tracking table
        cursor.execute(f"DELETE FROM {self._table}_map WHERE file_path = ?", (file_path,))
        self._connection.commit()

        logger.debug(f"Deleted summary for {file_path}")
        return 1

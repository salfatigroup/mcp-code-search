"""Is file indexed tool."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_is_file_indexed(mcp: FastMCP, components) -> None:
    """Register the is_file_indexed tool."""

    @mcp.tool()
    async def is_file_indexed(file_path: str) -> dict:
        """Check the indexing status of a specific file.

        Args:
            file_path: Path to the file relative to project root

        Returns:
            Indexing status details including status, chunk count, and any errors
        """
        from db.models import IndexedFile, IndexStatus

        logger.info(f"is_file_indexed called: file_path='{file_path}'")

        with components.db.session() as session:
            record = session.query(IndexedFile).filter_by(file_path=file_path).first()

            if not record:
                logger.debug(f"File not found in index: {file_path}")
                return {"indexed": False, "status": "not_found"}

            result = {
                "indexed": record.status == IndexStatus.COMPLETED,
                "status": record.status.value,
                "chunk_count": record.chunk_count,
                "error": record.error_message,
                "indexed_at": record.indexed_at.isoformat() if record.indexed_at else None,
            }
            logger.debug(f"File status: {result}")
            return result

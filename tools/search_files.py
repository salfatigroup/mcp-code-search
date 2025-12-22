"""Search files tool."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_search_files(mcp: FastMCP, components) -> None:
    """Register the search_files tool."""

    @mcp.tool()
    async def search_files(query: str, limit: int = 20) -> list[dict]:
        """Search for files by name or path pattern.

        Args:
            query: Filename or path pattern to search (e.g., "config", "test_")
            limit: Maximum number of results to return

        Returns:
            List of matching file paths with their indexing status
        """
        from db.models import IndexedFile

        logger.info(f"search_files called: query='{query}', limit={limit}")

        with components.db.session() as session:
            files = session.query(IndexedFile).filter(
                IndexedFile.file_path.ilike(f"%{query}%")
            ).limit(limit).all()

            results = [{"path": f.file_path, "status": f.status.value} for f in files]
            logger.info(f"Found {len(results)} matching files")
            return results

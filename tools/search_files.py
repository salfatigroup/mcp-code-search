"""Search files tool."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_search_files(mcp: FastMCP, components) -> None:
    """Register the search_files tool."""

    @mcp.tool()
    async def search_files(query: str, limit: int = 20) -> list[dict]:
        """Search for files by name or path pattern - Use for discovering related files and dependencies.

        **Use this tool when:**
        - Finding all files related to a feature (e.g., "auth", "payment", "user")
        - Locating test files before implementing features (e.g., "test_")
        - Discovering configuration files (e.g., "config", ".env", "settings")
        - Finding related components (e.g., "models", "views", "controllers")
        - Identifying migration or schema files before database changes
        - Locating utility and helper files to understand available tools

        **Implementation workflow:**
        1. Use this to find related files before implementing
        2. Use search_codebase to understand the code patterns in those files
        3. Use is_file_indexed to verify indexing status if search returns incomplete results
        4. Implement following discovered patterns and reusing existing utilities

        **Example queries:**
        - "test_api" - find all API test files
        - "model" - discover data models across the codebase
        - "handler" or "controller" - find request handlers
        - "util" or "helper" - locate utility modules to reuse
        - "migration" - find database migrations before schema changes
        - "config" or "settings" - understand configuration structure

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

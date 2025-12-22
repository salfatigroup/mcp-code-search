"""Search codebase tool."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_search_codebase(mcp: FastMCP, components) -> None:
    """Register the search_codebase tool."""

    @mcp.tool()
    async def search_codebase(query: str, limit: int = 10) -> list[dict]:
        """Search the codebase using semantic similarity.

        Args:
            query: Natural language search query describing what you're looking for
            limit: Maximum number of results to return (default 10)

        Returns:
            List of matching code chunks with file paths and line numbers
        """
        logger.info(f"search_codebase called: query='{query}', limit={limit}")
        results = components.vectorstore.search(query, k=limit)
        logger.info(f"Returning {len(results)} results")
        return results

"""Get indexing status tool."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_get_indexing_status(mcp: FastMCP, components) -> None:
    """Register the get_indexing_status tool."""

    @mcp.tool()
    async def get_indexing_status(compact: bool = True) -> dict:
        """Get the overall indexing status of the codebase.

        Args:
            compact: If True, return summary counts. If False, return per-file details.

        Returns:
            Indexing status summary or detailed per-file breakdown
        """
        logger.info(f"get_indexing_status called: compact={compact}")
        status = components.index_manager.get_status(compact=compact)
        logger.debug(f"Status: {status}")
        return status

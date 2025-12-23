"""Get indexing status tool."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_get_indexing_status(mcp: FastMCP, components) -> None:
    """Register the get_indexing_status tool."""

    @mcp.tool()
    async def get_indexing_status(compact: bool = True) -> dict:
        """Get the overall indexing status of the codebase - Use to ensure search reliability.

        **Use this tool when:**
        - Starting a new implementation session to verify index health
        - Search results seem incomplete or outdated
        - After making significant file changes to check re-indexing
        - Debugging indexing issues (use compact=False for details)
        - Understanding codebase coverage before major refactoring

        **Implementation workflow:**
        - Check at session start to ensure index is up-to-date
        - If many files are "pending", wait or trigger full re-index
        - If files show "failed" status, investigate before implementing
        - Use compact=False to get per-file details when debugging
        - High total count with low errors means reliable search results

        Args:
            compact: If True, return summary counts. If False, return per-file details.

        Returns:
            Indexing status summary or detailed per-file breakdown
        """
        logger.info(f"get_indexing_status called: compact={compact}")
        status = components.index_manager.get_status(compact=compact)
        logger.debug(f"Status: {status}")
        return status

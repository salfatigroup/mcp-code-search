"""Find callees tool - what functions does a symbol call."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_find_callees(mcp: FastMCP, components) -> None:
    """Register the find_callees tool."""

    @mcp.tool()
    async def find_callees(symbol: str, limit: int = 50) -> list[dict]:
        """Find all functions called by a specific function - ESSENTIAL for understanding dependencies.

        **ALWAYS use this tool before:**
        - Implementing similar functionality - reuse existing utility calls
        - Understanding what a function does - see its dependencies
        - Estimating complexity - count external dependencies
        - Identifying side effects - see database, API, or logging calls
        - Tracing data flow - follow the chain of function calls
        - Finding opportunities to extract common utilities

        **Why this is powerful:**
        - Reveals hidden dependencies and side effects
        - Shows the actual implementation approach vs assumptions
        - Identifies opportunities for code reuse and consolidation
        - Maps data flow and transformation pipelines
        - Exposes tight coupling that complicates testing

        **Example usage:**
        - Before implementing payment flow, see what process_payment() calls
        - Understanding authentication by checking what authenticate_user() does
        - Finding database access patterns by checking repository method calls
        - Discovering logging conventions by examining what functions call logger
        - Identifying external API usage by tracing API call chains

        Args:
            symbol: Function/method name to analyze
            limit: Maximum number of results (default: 50)

        Returns:
            List of called functions with file paths, line numbers, and external flags
        """
        from db.models import CodeRelationship

        logger.info(f"find_callees called: symbol='{symbol}', limit={limit}")

        with components.db.session() as session:
            # Find all calls made by this symbol
            relationships = session.query(CodeRelationship).filter(
                CodeRelationship.source_symbol == symbol,
                CodeRelationship.relationship_type == "calls"
            ).limit(limit).all()

            results = [{
                "callee": rel.target_symbol,
                "callee_file": rel.target_file,
                "call_line": rel.source_line,
                "is_external": rel.is_external
            } for rel in relationships]

            logger.info(f"Found {len(results)} callees for '{symbol}'")
            return results

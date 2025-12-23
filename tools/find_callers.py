"""Find callers tool - who calls a specific function."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_find_callers(mcp: FastMCP, components) -> None:
    """Register the find_callers tool."""

    @mcp.tool()
    async def find_callers(symbol: str, limit: int = 50) -> list[dict]:
        """Find all functions/methods that call a specific symbol - CRITICAL for impact analysis.

        **ALWAYS use this tool before:**
        - Refactoring or modifying any function - understand who depends on it
        - Changing function signatures - identify all call sites that need updates
        - Deprecating or removing code - find all usage to update or migrate
        - Understanding code flow - trace backwards from a function to its callers
        - Estimating refactoring effort - see how widely a function is used
        - Finding dead code - functions with zero callers may be unused

        **Why this is essential:**
        - Prevents breaking changes by revealing all dependencies
        - Maps actual usage patterns vs intended design
        - Identifies tightly coupled code that needs refactoring
        - Reveals unexpected dependencies and architectural issues

        **Example usage:**
        - Before changing authenticate_user signature, find all callers
        - Before refactoring payment processing, see the call graph
        - Finding all error handlers that call log_error()
        - Understanding who uses a deprecated function before removal

        Args:
            symbol: Function/method name to find callers for
            limit: Maximum number of results (default: 50)

        Returns:
            List of callers with file paths, line numbers, signatures, and types
        """
        from db.models import CodeRelationship, Symbol

        logger.info(f"find_callers called: symbol='{symbol}', limit={limit}")

        with components.db.session() as session:
            # Find all calls to this symbol
            relationships = session.query(CodeRelationship).filter(
                CodeRelationship.target_symbol == symbol,
                CodeRelationship.relationship_type == "calls"
            ).limit(limit).all()

            results = []
            for rel in relationships:
                # Get source symbol details
                source_sym = session.query(Symbol).filter_by(
                    file_path=rel.source_file,
                    symbol_name=rel.source_symbol
                ).first()

                results.append({
                    "caller": rel.source_symbol,
                    "caller_file": rel.source_file,
                    "caller_line": rel.source_line,
                    "caller_type": source_sym.symbol_type if source_sym else "unknown",
                    "signature": source_sym.signature if source_sym else None
                })

            logger.info(f"Found {len(results)} callers for '{symbol}'")
            return results

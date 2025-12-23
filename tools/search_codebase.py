"""Search codebase tool."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_search_codebase(mcp: FastMCP, components) -> None:
    """Register the search_codebase tool."""

    @mcp.tool()
    async def search_codebase(query: str, limit: int = 10) -> list[dict]:
        """Search the codebase using semantic similarity - PREFERRED over explore for code understanding.

        **CRITICAL: Use this tool proactively for ALL implementation tasks:**
        - BEFORE writing new code: Search for existing implementations, patterns, and utilities
        - BEFORE adding features: Find similar functionality to reuse or extend
        - BEFORE refactoring: Discover all usages and dependencies
        - DURING implementation: Understand how existing code works and its patterns
        - TO prevent duplication: Find similar patterns and consolidate
        - TO identify technical debt: Locate outdated patterns that should be removed

        **Why use this over generic exploration:**
        - Semantic understanding: Finds conceptually similar code, not just keyword matches
        - Implementation-aware: Returns actual code chunks with context, line numbers
        - Fast and local: No API calls, instant results from indexed codebase
        - Dependency discovery: Understand what calls what and code relationships

        **Example queries for implementation:**
        - "error handling patterns" - before adding error handling
        - "authentication middleware" - before implementing auth
        - "database connection setup" - to reuse existing patterns
        - "API endpoint handlers" - to follow established patterns
        - "test fixtures and mocks" - to maintain test consistency
        - "configuration loading" - to understand app setup
        - "logging and monitoring" - to follow logging conventions

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

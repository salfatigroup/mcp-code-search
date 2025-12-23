"""Get dependency tree tool - import/export relationships."""
import logging
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_get_dependency_tree(mcp: FastMCP, components) -> None:
    """Register the get_dependency_tree tool."""

    @mcp.tool()
    async def get_dependency_tree(
        file_path: str,
        depth: int = 3,
        direction: str = "both"
    ) -> dict:
        """Get dependency tree for a file - CRITICAL for understanding module relationships.

        **ALWAYS use this tool before:**
        - Modifying a core module - see who depends on it (blast radius)
        - Adding new dependencies - understand current import patterns
        - Refactoring module structure - map the dependency graph
        - Identifying circular dependencies - traverse both directions
        - Planning microservice extraction - find module boundaries
        - Understanding architecture - see how modules connect

        **Why this is essential:**
        - Reveals circular dependencies that complicate changes
        - Maps module coupling and architectural boundaries
        - Identifies God modules with too many dependencies
        - Shows ripple effects of changes through import chains
        - Guides safe refactoring by revealing dependent modules

        **Example usage:**
        - Before modifying api/auth.py, see what imports it (importers)
        - Understanding dependencies: what does models/user.py import? (imports)
        - Finding circular deps: get full graph with direction="both"
        - Planning extraction: map dependencies for utils/helpers.py
        - Architecture review: trace dependency chains from entry points

        **Direction options:**
        - "imports": What THIS file depends on (its dependencies)
        - "importers": What depends ON this file (its dependents)
        - "both": Complete picture of the file's position in the graph

        Args:
            file_path: File to analyze (relative to project root)
            depth: How many levels to traverse (default: 3, max: 10)
            direction: "imports", "importers", or "both" (default: "both")

        Returns:
            Dependency graph showing imports and/or importers with line numbers
        """
        from db.models import CodeRelationship

        logger.info(f"get_dependency_tree called: file='{file_path}', depth={depth}, direction={direction}")

        tree = {
            "file": file_path,
            "imports": [],
            "imported_by": []
        }

        with components.db.session() as session:
            if direction in ("imports", "both"):
                # What does this file import
                imports = session.query(CodeRelationship).filter(
                    CodeRelationship.source_file == file_path,
                    CodeRelationship.relationship_type == "imports"
                ).all()

                tree["imports"] = [{
                    "module": rel.target_symbol,
                    "line": rel.source_line,
                    "is_external": rel.is_external
                } for rel in imports]

            if direction in ("importers", "both"):
                # Who imports this file
                importers = session.query(CodeRelationship).filter(
                    CodeRelationship.target_symbol.like(f"%{Path(file_path).stem}%"),
                    CodeRelationship.relationship_type == "imports"
                ).limit(50).all()

                tree["imported_by"] = [{
                    "file": rel.source_file,
                    "line": rel.source_line
                } for rel in importers]

        logger.info(f"Dependency tree: {len(tree['imports'])} imports, {len(tree['imported_by'])} importers")
        return tree

"""MCP Code Search Server - Semantic code search via vector embeddings.

Usage:
    uv run main.py                    # stdio transport (default)
    mcp run main.py                   # via mcp CLI
"""
import sys
import logging
import subprocess
from pathlib import Path
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP

from settings.config import get_settings
from embedders import load_embedder
from chunkers import load_chunker
from db.connection import DatabaseManager
from db.vectorstore.sqlite import SQLiteVectorStore
from db.vectorstore.file_summaries import FileSummaryVectorStore
from index.manager import IndexManager
from index.worker import IndexWorker
from summarizers import SimpleSummarizer
from analyzers.tree_sitter import TreeSitterAnalyzer
from tools import (
    register_search_codebase,
    register_search_files,
    register_is_file_indexed,
    register_get_indexing_status,
    register_find_callers,
    register_find_callees,
    register_get_dependency_tree,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize settings at module level
settings = get_settings()


def validate_git_repo() -> None:
    """Validate that we're running in a git repository."""
    project_root = Path(settings.project_root).resolve()

    # Check if git repo
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=project_root,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        error_msg = f"""
ERROR: Not a git repository: {project_root}

MCP Code Search requires a git repository for indexing.

Solutions:
1. Initialize git in your project:
   cd {project_root} && git init

2. Set MCP_CS_PROJECT_ROOT to a git repository:
   export MCP_CS_PROJECT_ROOT=/path/to/your/git/repo

3. Add to your .env file:
   MCP_CS_PROJECT_ROOT=/path/to/your/git/repo
"""
        logger.error(error_msg)
        sys.exit(1)


def add_to_gitignore() -> None:
    """Add .mcp-code-search directory to .gitignore if not already present."""
    project_root = Path(settings.project_root).resolve()
    gitignore_path = project_root / ".gitignore"
    ignore_pattern = ".mcp-code-search/"

    # Read existing .gitignore or create empty list
    existing_lines = []
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            existing_lines = f.read().splitlines()

    # Check if pattern already exists
    if ignore_pattern.strip() in [line.strip() for line in existing_lines]:
        return

    # Add pattern to .gitignore
    try:
        with open(gitignore_path, "a") as f:
            if existing_lines and not existing_lines[-1].endswith("\n"):
                f.write("\n")
            f.write(f"\n# MCP Code Search database\n{ignore_pattern}\n")
        logger.info(f"Added {ignore_pattern} to {gitignore_path}")
    except Exception as e:
        logger.warning(f"Could not update .gitignore: {e}")

# Global component references (initialized in lifespan)
class Components:
    embedder = None
    chunker = None
    db = None
    vectorstore = None
    summary_store = None
    summarizer = None
    analyzer = None
    index_manager = None
    index_worker = None

components = Components()

@asynccontextmanager
async def lifespan(server: FastMCP):
    """Manage component lifecycle - runs on server startup/shutdown."""
    # Validate environment
    validate_git_repo()
    add_to_gitignore()

    # Initialize components on startup
    logger.info("Initializing embedder (first run downloads model ~1.2GB)...")
    components.embedder = load_embedder(settings)
    components.chunker = load_chunker(settings)
    components.db = DatabaseManager(settings.db_path)
    components.vectorstore = SQLiteVectorStore(settings.db_path, components.embedder)

    # Initialize optional components
    if settings.enable_summaries:
        logger.info("Initializing file summary components...")
        components.summary_store = FileSummaryVectorStore(settings.db_path, components.embedder)
        components.summarizer = SimpleSummarizer()  # Use simple rule-based summarizer

    if settings.enable_ast:
        logger.info("Initializing AST analyzer...")
        components.analyzer = TreeSitterAnalyzer()

    components.index_manager = IndexManager(
        settings,
        components.db,
        components.vectorstore,
        components.chunker,
        components.embedder,
        summarizer=components.summarizer,
        analyzer=components.analyzer,
        summary_store=components.summary_store,
    )
    components.index_worker = IndexWorker(settings, components.index_manager, components.chunker)

    # Start background indexing worker
    logger.info("Starting background indexing worker...")
    await components.index_worker.start()
    logger.info("MCP Code Search server ready!")

    yield  # Server runs here

    # Cleanup on shutdown
    logger.info("Shutting down...")
    await components.index_worker.stop()

# Create MCP server
mcp = FastMCP(name="mcp-code-search", lifespan=lifespan)

# Register tools
register_search_codebase(mcp, components)
register_search_files(mcp, components)
register_is_file_indexed(mcp, components)
register_get_indexing_status(mcp, components)

# Register AST tools if enabled
if settings.enable_ast:
    register_find_callers(mcp, components)
    register_find_callees(mcp, components)
    register_get_dependency_tree(mcp, components)

if __name__ == "__main__":
    mcp.run()
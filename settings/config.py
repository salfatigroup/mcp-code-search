"""Configuration settings using Pydantic."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="MCP_CS_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Paths
    project_root: str = Field(default=".", description="Root directory to index")
    db_path: str = Field(default=".mcp-code-search/db.sqlite")

    # Embedder
    embedder_type: str = Field(default="local")
    embedder_model: str = Field(default="intfloat/multilingual-e5-large-instruct")

    # Chunking
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)

    # Indexing
    index_interval: int = Field(default=300)
    ignore_patterns: list[str] = Field(
        default=[".git", "node_modules", ".venv", "__pycache__", ".mcp-code-search"]
    )
    file_extensions: list[str] = Field(
        default=[".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java", ".md", ".json"]
    )

    # File summarization
    enable_summaries: bool = Field(default=True, description="Enable AI file summarization")
    summarizer_model: str = Field(default="mistralai/Ministral-3-3B-Instruct-2512")
    summary_batch_size: int = Field(default=10, description="Number of files to summarize per batch")

    # AST analysis
    enable_ast: bool = Field(default=True, description="Enable AST-based code intelligence")
    ast_max_file_size: int = Field(default=100_000, description="Skip AST for files larger than this")


def get_settings() -> Settings:
    """Factory function to get settings instance."""
    return Settings()

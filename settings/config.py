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


def get_settings() -> Settings:
    """Factory function to get settings instance."""
    return Settings()

# MCP Code Intelligence

Intelligent code search MCP server with AST analysis, call graphs, dependency tracking, and semantic embeddings.

## Features

### Core Search
- **Semantic Code Search**: Vector-based similarity search across your codebase
- **Language-Aware Splitting**: Automatically detects and handles 25+ programming languages
- **Local-First**: Uses SQLite-vec for fast vector search without external services
- **Gitignore Support**: Respects `.gitignore` patterns automatically

### AST Intelligence (NEW)
- **Call Graph Analysis**: Track who-calls-what relationships
- **Symbol Extraction**: Index all functions, classes, and methods
- **Dependency Trees**: Map import/export relationships
- **Smart Search**: Find code by structure, not just keywords

### File Intelligence
- **Semantic File Search**: Find files by purpose, not just name
- **Auto-Summarization**: AI-generated file summaries
- **Background Indexing**: Automatically tracks file changes

## Installation

### Quick Start (Recommended)

```bash
# Run directly with uvx (no installation needed)
uvx mcp-code-intelligence
```

### Install as Tool

```bash
# Install permanently
uv tool install mcp-code-intelligence

# Run
mcp-code-intelligence
```

### Development Installation

```bash
# Clone repository
git clone https://github.com/salfatigroup/mcp-code-intelligence
cd mcp-code-intelligence

# Install dependencies
uv sync

# Run
uv run main.py
```

## Usage

### Standalone Testing

```bash
# Test the server directly
uv run main.py
```

### Configure in Claude Code

Add to your Claude Code MCP configuration file:

**Location:** `~/.config/claude-code/mcp.json` (Linux/Mac) or `%APPDATA%\claude-code\mcp.json` (Windows)

```json
{
  "mcpServers": {
    "code-intelligence": {
      "command": "uvx",
      "args": ["mcp-code-intelligence"],
      "env": {
        "MCP_CS_PROJECT_ROOT": "/path/to/your/project"
      }
    }
  }
}
```

**Advanced Configuration:**

```json
{
  "mcpServers": {
    "code-intelligence": {
      "command": "uvx",
      "args": ["mcp-code-intelligence"],
      "env": {
        "MCP_CS_PROJECT_ROOT": "/Users/username/my-project",
        "MCP_CS_INDEX_INTERVAL": "600",
        "MCP_CS_ENABLE_AST": "true",
        "MCP_CS_ENABLE_SUMMARIES": "true"
      }
    }
  }
}
```

**For Development (from source):**

```json
{
  "mcpServers": {
    "code-intelligence": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-code-intelligence", "run", "main.py"],
      "env": {
        "MCP_CS_PROJECT_ROOT": "/path/to/project"
      }
    }
  }
}
```

### Configure in Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "code-intelligence": {
      "command": "uvx",
      "args": ["mcp-code-intelligence"],
      "env": {
        "MCP_CS_PROJECT_ROOT": "/path/to/your/project"
      }
    }
  }
}
```

### Verify Installation

After adding the configuration:

1. **Restart Claude Code/Desktop**
2. **Check server status** - You should see "code-search" in the MCP servers list
3. **Test a search** - Try asking: "Search for authentication logic in the codebase"

The first run will:
- ✅ Validate git repository
- ✅ Add `.mcp-code-search/` to your project's `.gitignore`
- ✅ Download the embedding model (~1.2GB, one-time)
- ✅ Index all git-tracked files
- ✅ Start background monitoring for changes

### Configuration

Configure via environment variables with `MCP_CS_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_CS_PROJECT_ROOT` | `.` | Root directory to index |
| `MCP_CS_DB_PATH` | `.mcp-code-search/db.sqlite` | SQLite database path |
| `MCP_CS_EMBEDDER_MODEL` | `intfloat/multilingual-e5-large-instruct` | HuggingFace model name |
| `MCP_CS_CHUNK_SIZE` | `1000` | Chunk size in characters |
| `MCP_CS_CHUNK_OVERLAP` | `200` | Chunk overlap in characters |
| `MCP_CS_INDEX_INTERVAL` | `300` | Background index interval (seconds) |

Example `.env`:
```bash
MCP_CS_PROJECT_ROOT=/path/to/your/project
MCP_CS_INDEX_INTERVAL=600
```

## MCP Tools (7 Total)

### Core Search Tools

**1. `search_codebase(query, limit=10)`**
- Semantic code search using vector similarity
- Returns matching code chunks with file paths and line numbers

**2. `search_files(query, limit=20, semantic=true)`**
- Search files by name OR semantic similarity
- With `semantic=true`: finds files by purpose
- With `semantic=false`: pattern matching on filenames

**3. `is_file_indexed(file_path)`**
- Check if a file is indexed and its status
- Returns chunk count, errors, indexing timestamp

**4. `get_indexing_status(compact=true)`**
- Overall indexing health check
- Compact: summary counts
- Detailed: per-file breakdown

### AST Intelligence Tools (NEW)

**5. `find_callers(symbol, limit=50)`**
- Find all functions that call a specific function/method
- Critical before refactoring - understand impact
- Returns callers with file paths, line numbers, signatures

**6. `find_callees(symbol, limit=50)`**
- Find all functions called BY a specific function
- Understand dependencies and data flow
- Returns callees with context and external flags

**7. `get_dependency_tree(file_path, depth=3, direction="both")`**
- Map import/export relationships
- `direction="imports"`: what file depends on
- `direction="importers"`: what depends on file
- `direction="both"`: complete dependency graph

## Architecture

### Project Structure

```
mcp-code-search/
├── main.py                   # FastMCP server + tools
├── settings/                 # Pydantic settings
├── embedders/                # Embedding providers
├── chunkers/                 # Language-aware text splitters
├── db/                       # Database & vector store
│   └── vectorstore/          # SQLite-vec integration
└── index/                    # Indexing logic
    ├── delta.py              # Git delta detection
    ├── gitignore.py          # .gitignore filtering
    ├── manager.py            # Indexing orchestration
    └── worker.py             # Background worker
```

### Supported Languages

Python, JavaScript/TypeScript, Go, Rust, C/C++, Java, Kotlin, Scala, Ruby, PHP, Swift, C#, Lua, Perl, Haskell, Elixir, Solidity, Protobuf, PowerShell, HTML, Markdown, LaTeX, RST

### How It Works

1. **Startup**: Initializes embedder, chunker, database, and vector store
2. **Initial Index**: Scans git-tracked files and indexes supported file types
3. **Background Indexing**: Periodically checks for changed files via git delta
4. **Search**: Embeds queries and performs vector similarity search
5. **Gitignore**: Respects `.gitignore` patterns to exclude files

## Troubleshooting

### "Not a git repository" Error

The server requires a git repository for indexing. Solutions:

```bash
# Option 1: Initialize git in your project
cd /path/to/your/project
git init

# Option 2: Set project root to a git repo
export MCP_CS_PROJECT_ROOT=/path/to/git/repo

# Option 3: Add to .env file
echo "MCP_CS_PROJECT_ROOT=/path/to/git/repo" >> .env
```

### Model Download Issues

First run downloads ~1.2GB embedding model. If it fails:

```bash
# Manually download model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-large-instruct')"
```

### Performance Tips

- **Chunk Size**: Larger chunks = fewer but longer results
- **Index Interval**: Higher interval = less CPU usage
- **Ignore Patterns**: Add large binary/generated files to speed up indexing

```bash
# Environment variables for tuning
export MCP_CS_CHUNK_SIZE=1500        # Larger chunks
export MCP_CS_INDEX_INTERVAL=900     # Index every 15 min
```

## Development

### Requirements

- Python 3.13+
- PyTorch (for embeddings)
- Git (for delta detection)

### Device Detection

Automatically detects best device:
- CUDA (NVIDIA GPUs)
- MPS (Apple Silicon)
- CPU (fallback)

### Project Structure

All code follows the architecture in the implementation plan:
- **settings/**: Pydantic configuration
- **embedders/**: Embedding providers with device detection
- **chunkers/**: Language-aware text splitters
- **db/**: Database models and SQLite-vec integration
- **index/**: Git delta, gitignore filtering, background worker

## Examples

### Using in Claude Code

```
User: "Search for error handling code"
Assistant: *Uses search_codebase tool*
Found error handling in:
- src/api/handler.py:45-67
- src/utils/errors.py:12-34

User: "Find all test files"
Assistant: *Uses search_files tool with query="test_"*
Found test files:
- tests/test_api.py
- tests/test_utils.py
```

### Checking Index Status

```
User: "What files are indexed?"
Assistant: *Uses get_indexing_status(compact=True)*
Total: 234 files
- completed: 230
- in_progress: 2
- failed: 2
```

## License

See LICENSE file.

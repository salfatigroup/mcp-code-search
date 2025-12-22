The idea behind this MCP server is to be able to index the codebase of a project through smart vector embeddings and vector search on a local environment with option for remote vendors for embedding providers or storage providers.

By default we will use local embeddings (assuming macos and laptop can support it, probably e5-instruct?) and local storage with sqlite (langchain vector store sqlitevec)

## Implementation Logic
- load_embedder class/function that loads the embedder from the config - default to local e5-instruct (apple silicon)
- load_vectorstore class/function that loads the vectorstore from the config - default to local with sqlitevec (langchain vector store sqlitevec)
- load_chunker class/function that loads the chunker based on the config, default to recursive character text splitter for codebase - also langchain.
- load settings - using pydantic and pydantic-settings

## Tools
- search_files - to search the file by name and short description of the content of the file.
- search_codebase - to search the chunks
- is_file_indexed - to check if the file is indexed or what's its indexing status - queued, in progress, completed, failed, etc.
- get_indexing_status(compact / detailed) - to get the indexing status of the file or the codebase.

Ideally indexing should be done in the background on the deltas we get - probably through git? interval should be configurable on settings.

## Stack
- langchain (latest, v1.1)
- pydantic
- pydantic-settings
- https://modelcontextprotocol.io/docs/develop/build-server mcp server - fastmcp
- sqlite (langchain vector store sqlitevec)
- text splitting (langchain)
- embedding model - local - [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) or [multilingual-e5-large-instruct](https://huggingface.co/intfloat/multilingual-e5-large-instruct) or [embeddinggemma-300m](https://ai.google.dev/gemma/docs/embeddinggemma/model_card)



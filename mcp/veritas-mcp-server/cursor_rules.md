# VeritasGraph MCP Server - Cursor Rules

You are working with the VeritasGraph MCP Server, which exposes GraphRAG knowledge graph functionality through the Model Context Protocol (MCP).

## Project Structure

```
veritas-mcp-server/
├── veritas_mcp_server.py   # Main MCP server with FastMCP tools
├── pyproject.toml          # Python project configuration
├── README.md               # Documentation
├── Dockerfile              # Container build
├── docker-compose.yml      # Container orchestration
├── .env.example            # Environment template
├── mcp_config_stdio_example.json  # Claude Desktop config (stdio)
└── mcp_config_sse_example.json    # Claude Desktop config (SSE)
```

## MCP Tools Available

1. **query_graph** - Query the knowledge graph (local/global search)
2. **ingest_text** - Add text documents
3. **ingest_url** - Add content from URLs
4. **trigger_index** - Build/update knowledge graph
5. **get_index_status** - Check indexing progress
6. **list_files** - List input documents
7. **delete_file** - Remove documents
8. **health_check** - System status
9. **get_graph_stats** - Graph statistics

## Key Dependencies

- `mcp` / `fastmcp` - MCP server framework
- `graphrag` - Microsoft GraphRAG for knowledge graphs
- `tiktoken` - Token counting
- `pandas` / `pyarrow` - Data handling
- `lancedb` - Vector store

## Configuration

Environment variables:
- `GRAPHRAG_API_KEY` - LLM API key
- `GRAPHRAG_LLM_API_BASE` - LLM endpoint URL
- `GRAPHRAG_LLM_MODEL` - Model name
- `VERITAS_OUTPUT_DIR` - GraphRAG artifacts path
- `VERITAS_INPUT_DIR` - Input documents path

## Code Style

- Use type hints
- Async/await for I/O operations
- Pydantic for data validation
- Comprehensive docstrings for MCP tools
- Error handling returns dict with 'error' key

## Testing

Run the server locally:
```bash
python veritas_mcp_server.py --transport stdio
```

Test with MCP Inspector or Claude Desktop.

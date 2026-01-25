# 🔌 VeritasGraph MCP Server

> Transform VeritasGraph from a standalone app into a **plugin** that works where users already work — Claude Desktop, Cursor, and any MCP-compatible AI agent.

[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is This?

The **VeritasGraph MCP Server** exposes GraphRAG-powered knowledge graph queries as [Model Context Protocol (MCP)](https://modelcontextprotocol.io) tools. This means you can:

- 🔍 **Query your knowledge graph** directly from Claude Desktop or Cursor
- 📥 **Ingest new documents** without leaving your AI assistant
- 🔄 **Trigger indexing** to update the knowledge graph
- 📊 **Get graph statistics** and health information

## Features

| Tool | Description |
|------|-------------|
| `query_graph` | Query the knowledge graph using local or global search |
| `ingest_text` | Add text documents to the knowledge base |
| `ingest_url` | Extract and ingest content from URLs (web pages, YouTube) |
| `trigger_index` | Build/update the knowledge graph from documents |
| `get_index_status` | Check indexing progress |
| `list_files` | List documents in the input directory |
| `delete_file` | Remove a document from the input directory |
| `health_check` | Check system status and configuration |
| `get_graph_stats` | Get entity, relationship, and community counts |

## Quick Start

### 1. Installation

```bash
# Navigate to the VeritasGraph directory
cd VeritasGraph

# Use the existing virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\python.exe -m pip install mcp fastmcp

# On Windows (Command Prompt):
.venv\Scripts\python.exe -m pip install mcp fastmcp

# On Linux/Mac:
.venv/bin/python -m pip install mcp fastmcp
```

Or if you prefer activating the venv first:
```bash
# Windows PowerShell (may need execution policy change)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
pip install mcp fastmcp

# Windows CMD
.venv\Scripts\activate.bat
pip install mcp fastmcp

# Linux/Mac
source .venv/bin/activate
pip install mcp fastmcp
```

### 2. Configure Environment

The MCP server automatically loads the `.env` file from `graphrag-ollama-config/`. 
Ensure your LLM settings are configured there:

```env
# For Ollama (default)
GRAPHRAG_API_KEY=ollama
GRAPHRAG_LLM_MODEL=llama3.1:latest
GRAPHRAG_LLM_API_BASE=http://localhost:11434/v1
GRAPHRAG_EMBEDDING_MODEL=nomic-embed-text
GRAPHRAG_EMBEDDING_API_BASE=http://localhost:11434/v1
```

### 3. Run the Server

**For testing (stdio mode):**
```bash
cd VeritasGraph/mcp/veritas-mcp-server
..\..\..\.venv\Scripts\python.exe veritas_mcp_server.py --transport stdio
```

**For network access (SSE mode):**
```bash
cd VeritasGraph/mcp/veritas-mcp-server
..\..\..\.venv\Scripts\python.exe veritas_mcp_server.py --transport sse
```

### 4. Verify Installation

Run the quick test to verify everything works:
```bash
cd VeritasGraph/mcp/veritas-mcp-server
..\..\..\.venv\Scripts\python.exe quick_test.py
```

Expected output:
```
Testing health_check...
  Status: healthy
  Index Ready: True

Testing get_graph_stats...
  Entities: 223
  Relationships: 150
  Communities: 5

✅ All tests passed!
```

## HTTP REST API (for Testing)

The server includes a simple HTTP REST API mode for easy testing with curl/Postman:

### Start HTTP Server

```bash
cd VeritasGraph/mcp/veritas-mcp-server
..\..\..\.venv\Scripts\python.exe veritas_mcp_server.py --transport http --port 8001
```

### curl Commands

```bash
# Health check
curl http://127.0.0.1:8001/health

# Graph statistics
curl http://127.0.0.1:8001/stats

# List files
curl http://127.0.0.1:8001/files

# Index status
curl http://127.0.0.1:8001/status

# Query the knowledge graph (POST)
curl -X POST "http://127.0.0.1:8001/query?query=What%20are%20the%20main%20topics&search_type=local"

# Ingest text content (POST)
curl -X POST "http://127.0.0.1:8001/ingest?title=Test%20Doc&content=This%20is%20test%20content"
```

### Postman Setup

| Method | URL | Description |
|--------|-----|-------------|
| GET | `http://127.0.0.1:8001/health` | Health check |
| GET | `http://127.0.0.1:8001/stats` | Graph statistics |
| GET | `http://127.0.0.1:8001/files` | List input files |
| GET | `http://127.0.0.1:8001/status` | Index status |
| POST | `http://127.0.0.1:8001/query?query=YOUR_QUERY&search_type=local` | Query graph |
| POST | `http://127.0.0.1:8001/ingest?title=TITLE&content=CONTENT` | Ingest text |

### PowerShell Test

```powershell
# Health check
Invoke-RestMethod http://127.0.0.1:8001/health

# Graph statistics
Invoke-RestMethod http://127.0.0.1:8001/stats

# Query the graph
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/query?query=What are the main topics&search_type=local"
```

## Integration with AI Assistants

### Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

**Option A: stdio (recommended for local use)**
```json
{
  "mcpServers": {
    "veritasgraph": {
      "command": "python",
      "args": [
        "C:/Projects/graphrag/VeritasGraph/mcp/veritas-mcp-server/veritas_mcp_server.py",
        "--transport", "stdio"
      ],
      "env": {
        "GRAPHRAG_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Option B: SSE (for network/remote access)**
```json
{
  "mcpServers": {
    "veritasgraph": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

### Cursor

Add to your Cursor MCP settings:

```json
{
  "mcpServers": {
    "veritasgraph": {
      "command": "python",
      "args": [
        "C:/Projects/graphrag/VeritasGraph/mcp/veritas-mcp-server/veritas_mcp_server.py"
      ]
    }
  }
}
```

### Other MCP Clients

Any MCP-compatible client can connect using either:
- **stdio transport**: Launch the server as a subprocess
- **SSE transport**: Connect to `http://host:port/sse`

## Usage Examples

Once connected, you can use natural language with your AI assistant:

### Querying the Knowledge Graph

```
"Search for information about authentication methods in my documents"
→ Uses query_graph with local search

"Give me a comprehensive summary of all the topics in my knowledge base"
→ Uses query_graph with global search
```

### Ingesting Content

```
"Add this meeting notes to my knowledge base: [paste content]"
→ Uses ingest_text

"Ingest this article: https://example.com/interesting-article"
→ Uses ingest_url
```

### Managing the Graph

```
"What's the status of my knowledge graph?"
→ Uses health_check

"How many entities are in my graph?"
→ Uses get_graph_stats

"Rebuild the knowledge graph index"
→ Uses trigger_index
```

## Search Types Explained

### Local Search 🔍
Best for: **Specific questions about entities and relationships**

- Uses vector similarity + graph traversal
- Returns detailed, focused answers
- Example: "What are the requirements for user authentication?"

### Global Search 🌐
Best for: **Broad questions requiring synthesis**

- Uses community reports and summarization
- Returns comprehensive, synthesized answers
- Example: "What are the main themes across all documents?"

## Response Types

| Type | Description |
|------|-------------|
| `Single Paragraph` | Brief, concise answer |
| `Multiple Paragraphs` | Detailed explanation (default) |
| `List of 3-7 Points` | Bullet point format |
| `Single Page` | Comprehensive single-page response |
| `Multi-Page Report` | In-depth analysis |

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VERITAS_OUTPUT_DIR` | Path to GraphRAG output artifacts | `graphrag-ollama-config/output/artifacts` |
| `VERITAS_INPUT_DIR` | Path to input documents | `graphrag-ollama-config/input` |
| `VERITAS_COMMUNITY_LEVEL` | Default community depth (1-5) | `2` |
| `VERITAS_TEMPERATURE` | LLM temperature (0.0-1.0) | `0.5` |
| `VERITAS_RESPONSE_TYPE` | Default response format | `Multiple Paragraphs` |

### Command Line Options

```bash
python veritas_mcp_server.py \
  --transport stdio|sse \
  --host 127.0.0.1 \
  --port 8000 \
  --output-dir /path/to/output \
  --input-dir /path/to/input
```

## Architecture

```
┌─────────────────────┐
│   Claude Desktop    │
│   Cursor / Agents   │
└─────────┬───────────┘
          │ MCP Protocol
          │ (stdio or SSE)
┌─────────▼───────────┐
│  VeritasGraph MCP   │
│       Server        │
│  ┌───────────────┐  │
│  │  FastMCP      │  │
│  │  Tools        │  │
│  └───────┬───────┘  │
└──────────┼──────────┘
           │
┌──────────▼──────────┐
│    GraphRAG Core    │
│  ┌───────────────┐  │
│  │ Local Search  │  │
│  │ Global Search │  │
│  │ Ingest/Index  │  │
│  └───────────────┘  │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Knowledge Graph    │
│  (Parquet + Lance)  │
└─────────────────────┘
```

## Troubleshooting

### "GraphRAG modules not available"
Ensure graphrag is installed: `pip install graphrag`

### "Index not ready"
Run `trigger_index` to build the knowledge graph from your documents.

### "No input files found"
Add documents to the input directory or use `ingest_text`/`ingest_url`.

### Connection refused (SSE mode)
Check that the server is running and the port is not blocked by firewall.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
ruff check .
```

## License

MIT License - see [LICENSE](../../LICENSE) for details.

## Related Projects

- [GraphRAG](https://github.com/microsoft/graphrag) - Microsoft's Graph RAG implementation
- [Model Context Protocol](https://modelcontextprotocol.io) - The MCP specification
- [FastMCP](https://github.com/jlowin/fastmcp) - Fast MCP server framework

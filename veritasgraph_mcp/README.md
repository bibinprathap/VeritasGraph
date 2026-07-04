# VeritasGraph MCP Server

mcp-name: io.github.bibinprathap/veritasgraph

**The first zero-trust, air-gapped Enterprise GraphRAG server for the
[Model Context Protocol](https://modelcontextprotocol.io/).**

Connect your local IDE agent — Claude Desktop, Cursor, VS Code, Windsurf,
Cline, Continue — directly to the VeritasGraph knowledge-graph engine over a
standard JSON-RPC 2.0 stdio stream. Build graphs from your documents, run
multi-hop graph-grounded queries with verifiable `[doc#chunk]` citations, and
inspect entities — all **100% locally**, with **zero external data egress**.

- **Zero-trust / air-gapped** — stdlib-only JSON-RPC server; no cloud calls, no
  telemetry. The only network hop is your local Ollama runtime.
- **Verifiable attribution** — every node and edge records the source chunk it
  came from, so answers cite their evidence.
- **Drop-in** — wraps the same `studio_api.graphrag_engine` used by Studio.

---

## Tools

| Tool | Purpose |
|------|---------|
| `veritasgraph_ingest_document` | Chunk a document, extract entities/relationships, merge into the graph. |
| `veritasgraph_query` | Multi-hop, graph-grounded answer with citations and reasoning path. |
| `veritasgraph_search_entities` | Fast subgraph retrieval for a query (no LLM call). |
| `veritasgraph_get_graph` | Return the full graph: nodes, edges, stats. |
| `veritasgraph_clear_graph` | Clear the entire graph (destructive). |

## Resources

| URI | Description |
|-----|-------------|
| `veritasgraph://graph` | Live snapshot of the knowledge graph. |
| `veritasgraph://stats` | Entity / relationship / source counts. |

---

## Requirements

- Python 3.10+
- VeritasGraph repo dependencies: `pip install -r requirements.txt`
- A local [Ollama](https://ollama.com) runtime with a chat model pulled
  (ingest/query need a model; `search_entities`/`get_graph` do not):

  ```bash
  ollama serve & ollama pull qwen3:latest
  ```

## Run it

```bash
# From the repository root
python -m veritasgraph_mcp            # stdio JSON-RPC server
python -m veritasgraph_mcp --debug    # verbose logging on stderr
```

### Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `VERITASGRAPH_MODEL` | `qwen3:latest` | Default Ollama model for ingest/query. |
| `OLLAMA_HOST` | `127.0.0.1:11434` | Local Ollama endpoint. |
| `STUDIO_DATA_DIR` | `studio_api/data` | Where the graph snapshot is persisted. |

---

## Use it through VeritasGraph Studio

The same tools and resources are exposed over HTTP by the Studio backend, so you
can drive the MCP server without an IDE — and the Studio agent pipeline can call
its tools directly.

Start the Studio API and the bridge mounts under `/mcp`:

```bash
uvicorn studio_api.main:app --port 8200
```

| Method & path | Purpose |
|---------------|---------|
| `GET /mcp/` | Server identity, capabilities, tool/resource counts. |
| `GET /mcp/tools` | List tool definitions (same schema as `tools/list`). |
| `POST /mcp/tools/{name}` | Invoke one tool; body is the tool arguments. |
| `GET /mcp/resources` | List `veritasgraph://` resources. |
| `GET /mcp/resources/read?uri=...` | Read a resource. |
| `POST /mcp/rpc` | Full JSON-RPC 2.0 bridge (any MCP method over HTTP). |

Two ready-to-use tools are pre-registered in the Studio **Tools** section
(*VeritasGraph MCP · Query* and *VeritasGraph MCP · Search*), pointing at loopback
`/mcp/tools/...` endpoints. Enable **Tools** on an agent to have the orchestrator
invoke them automatically during a run.

```bash
# Example: call a tool via the bridge
curl -s http://127.0.0.1:8200/mcp/tools/veritasgraph_search_entities \
  -H 'Content-Type: application/json' -d '{"query": "acme corp"}'
```

---

## Register in your IDE

Replace `/abs/path/to/VeritasGraph` with the absolute path to your clone, and
point `command` at the repo's Python (e.g. `.venv/bin/python`).

### Claude Desktop — `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "veritasgraph": {
      "command": "/abs/path/to/VeritasGraph/.venv/bin/python",
      "args": ["-m", "veritasgraph_mcp"],
      "cwd": "/abs/path/to/VeritasGraph",
      "env": { "VERITASGRAPH_MODEL": "qwen3:latest" }
    }
  }
}
```

### Cursor — `.cursor/mcp.json`

```json
{
  "mcpServers": {
    "veritasgraph": {
      "command": "/abs/path/to/VeritasGraph/.venv/bin/python",
      "args": ["-m", "veritasgraph_mcp"],
      "cwd": "/abs/path/to/VeritasGraph"
    }
  }
}
```

### VS Code — `.vscode/mcp.json`

```json
{
  "servers": {
    "veritasgraph": {
      "type": "stdio",
      "command": "/abs/path/to/VeritasGraph/.venv/bin/python",
      "args": ["-m", "veritasgraph_mcp"],
      "cwd": "/abs/path/to/VeritasGraph"
    }
  }
}
```

Windsurf, Cline, and Continue use the same `command` / `args` / `cwd` shape.

---

## Quick manual test (no IDE)

Pipe raw JSON-RPC frames over stdio:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"veritasgraph_get_graph","arguments":{}}}' \
  | python -m veritasgraph_mcp
```

You should get three JSON-RPC responses: server info, the tool catalog, and the
current graph snapshot.

---

## How it fits VeritasGraph

The MCP server is a thin protocol adapter. All graph construction, multi-hop
retrieval, and citation logic live in
[`studio_api/graphrag_engine.py`](../studio_api/graphrag_engine.py), the same
engine that powers Studio. That means the MCP surface, the Studio UI, and the
HTTP API all read and write the **same** local knowledge graph.

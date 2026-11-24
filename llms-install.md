# Installing the VeritasGraph MCP server

These steps are for AI agents (Cline, Claude Code, Cursor and others) that set up MCP servers for a user.

## Requirements

1. Python 3.10 or newer, and [uv](https://docs.astral.sh/uv/) so that `uvx` is available.
2. [Ollama](https://ollama.com) running locally, with a model pulled. Only `veritasgraph_query` and `veritasgraph_ingest_document` need it:

   ```bash
   ollama pull qwen3:latest
   ```

   The lookup tools (`veritasgraph_check_answerable`, `veritasgraph_search_entities`, `veritasgraph_get_entity` and the others) work without a model.

## Configuration

Add this to the client's MCP settings file (for Cline, `cline_mcp_settings.json`):

```json
{
  "mcpServers": {
    "veritasgraph": {
      "command": "uvx",
      "args": ["veritasgraph-mcp"],
      "env": {
        "VERITASGRAPH_MODEL": "qwen3:latest",
        "VERITASGRAPH_MCP_MODE": "write"
      }
    }
  }
}
```

Optional environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `VERITASGRAPH_MCP_MODE` | `write` | `read` exposes query tools only. `write` adds ingest and term proposals. `admin` adds import and clear. |
| `VERITASGRAPH_MODEL` | `qwen3:latest` | Ollama model for ingest and answers. |
| `OLLAMA_HOST` | `127.0.0.1:11434` | Ollama address. |
| `STUDIO_DATA_DIR` | `~/.veritasgraph` | Where the graph is stored. Use an absolute path. |

Do not set `VERITASGRAPH_MCP_MODE=admin` unless the user asks for it, because `veritasgraph_clear_graph` deletes the graph.

## Check that it works

1. Restart the client and confirm that the `veritasgraph` server lists its tools.
2. Call `veritasgraph_ingest_document` with a short text, for example `{"text": "Acme Corp acquired Beta Ltd in 2021.", "title": "demo"}`.
3. Call `veritasgraph_query` with `{"question": "Who acquired Beta Ltd?"}`. The answer should include `[doc#chunk]` citations and report `"grounded": true` when its citations match the retrieved evidence.

## Without uv

```bash
pip install veritasgraph-mcp
```

Then use `"command": "veritasgraph-mcp"` with no `args`.

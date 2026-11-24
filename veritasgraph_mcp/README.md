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

[![PyPI](https://img.shields.io/pypi/v/veritasgraph-mcp)](https://pypi.org/project/veritasgraph-mcp/)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-io.github.bibinprathap%2Fveritasgraph-blue)](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.bibinprathap/veritasgraph)
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_MCP_server-0098FF?logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=veritasgraph&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22veritasgraph-mcp%22%5D%7D)
[![Install in VS Code Insiders](https://img.shields.io/badge/VS_Code_Insiders-Install_MCP_server-24bfa5?logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=veritasgraph&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22veritasgraph-mcp%22%5D%7D&quality=insiders)
[![Install in Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=veritasgraph&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJ2ZXJpdGFzZ3JhcGgtbWNwIl19)

## Quick start

```bash
ollama pull qwen3:latest                              # once; any local chat model works
uvx veritasgraph-mcp                                  # run the server over stdio
claude mcp add veritasgraph -- uvx veritasgraph-mcp   # or register it in Claude Code
```

The graph is stored in `~/.veritasgraph` unless you set `STUDIO_DATA_DIR`.

---

## Tools

Tools are tiered by `VERITASGRAPH_MCP_MODE` (`read`, `write` *(default)*,
`admin`). Each tier includes the one below it.

| Tier | Tool | Purpose |
|------|------|---------|
| read | `veritasgraph_check_answerable` | Whether the graph (and, in governed mode, the certified glossary) can answer a question, before spending a model call. |
| read | `veritasgraph_query` | Multi-hop, graph-grounded answer with citations, reasoning path and an `answer_id` receipt. `mode`: `exploratory` or `governed`. |
| read | `veritasgraph_search_entities` | Fast subgraph retrieval for a query (no LLM call). |
| read | `veritasgraph_get_entity` | One entity with its relations and source chunks. |
| read | `veritasgraph_get_graph` | The full graph: nodes, edges, stats. |
| read | `veritasgraph_get_ontology` | Entity types, predicates and glossary terms with their status. |
| read | `veritasgraph_search_terms` / `veritasgraph_get_term` | Search or fetch business-glossary terms. |
| read | `veritasgraph_get_answer_receipt` | Replay a past answer by `answer_id`. |
| read | `veritasgraph_compile_status` | Latest ontology-compile run and pending suggestions. |
| read | `veritasgraph_structured_search` / `_get_term` / `_list_measures` / `_ask` | Governed semantic layer over SQL sources (needs the `structured` extra). |
| write | `veritasgraph_ingest_document` | Chunk a document, extract entities/relationships, merge into the graph. |
| write | `veritasgraph_import_graph` | Import a `graph.json` (Graphify, Understand-Anything, AI-Atlas, generic). |
| write | `veritasgraph_propose_term` | Propose a glossary term for admin certification. |
| admin | `veritasgraph_clear_graph` | Clear the graph (a snapshot is taken first). |

Tools outside the active tier are hidden and return JSON-RPC `-32601`.

Every tool has a `title` and annotations (`readOnlyHint`, `destructiveHint`,
`idempotentHint`), so clients can auto-approve read tools and ask before
`veritasgraph_clear_graph`. `check_answerable` and `query` also return
`structuredContent` that matches their `outputSchema`.

## Prompts

| Prompt | Argument | What it does |
|--------|----------|--------------|
| `grounded_answer` | `question` | Checks answerability, then answers with `[doc#chunk]` citations and the `answer_id`. |
| `verify_claim` | `claim` | Labels a statement SUPPORTED, CONTRADICTED or NOT IN GRAPH, with citations. |
| `explore_entity` | `entity` | Summarises an entity, its relationships and their sources. |

## Resources

| URI | Description |
|-----|-------------|
| `veritasgraph://graph` | Live snapshot of the knowledge graph. |
| `veritasgraph://stats` | Entity / relationship / source counts. |
| `veritasgraph://ontology` | The governed vocabulary (types, predicates, terms). |

---

## Requirements

- Python 3.10+ (or Docker)
- A local [Ollama](https://ollama.com) runtime with a chat model pulled
  (ingest/query need a model; `search_entities`/`get_graph` do not):

  ```bash
  ollama serve & ollama pull qwen3:latest
  ```

## Run it

```bash
uvx veritasgraph-mcp                  # from PyPI with uv
pip install veritasgraph-mcp && veritasgraph-mcp
docker run --rm -i -v veritasgraph:/data ghcr.io/bibinprathap/veritasgraph-mcp

# From a clone of the repository
python -m veritasgraph_mcp            # stdio JSON-RPC server
python -m veritasgraph_mcp --debug    # verbose logging on stderr
```

In Docker, reach Ollama on the host with `-e OLLAMA_HOST=host.docker.internal:11434`
(on Linux also add `--add-host=host.docker.internal:host-gateway`). The image
defaults to `VERITASGRAPH_MCP_MODE=read`.

### Streamable HTTP

```bash
VERITASGRAPH_MCP_TOKEN=$(openssl rand -hex 24) veritasgraph-mcp --transport http --port 8765
```

Clients POST JSON-RPC to `http://127.0.0.1:8765/mcp`; `GET /healthz` is a
liveness probe. The server binds to `127.0.0.1` by default, rejects browser
`Origin` headers that are not loopback or listed in
`VERITASGRAPH_MCP_ALLOWED_ORIGINS`, and requires `Authorization: Bearer <token>`
when `VERITASGRAPH_MCP_TOKEN` is set. Keep a token set whenever you bind to
anything other than loopback. The Docker image switches to HTTP on `0.0.0.0`
when `PORT` is set.

### Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `VERITASGRAPH_MODEL` | `qwen3:latest` | Default Ollama model for ingest/query. |
| `OLLAMA_HOST` | `127.0.0.1:11434` | Local Ollama endpoint. |
| `VERITASGRAPH_MCP_MODE` | `write` | Tool tier: `read`, `write` or `admin`. Use `read` for untrusted clients. |
| `STUDIO_DATA_DIR` | `~/.veritasgraph` (`studio_api/data` in a clone) | Data directory. |
| `VERITASGRAPH_DB` | `$STUDIO_DATA_DIR/veritasgraph.db` | SQLite graph store shared with Studio and the CLI. |
| `VERITASGRAPH_PII_POLICY` | `tag` | `off`, `tag`, `redact_before_extract` or `reject`. |
| `VERITASGRAPH_MCP_TRANSPORT` | `stdio` | `stdio` or `http` (same as `--transport`). |
| `VERITASGRAPH_MCP_HOST` / `VERITASGRAPH_MCP_PORT` | `127.0.0.1` / `8765` | HTTP bind address and port. |
| `VERITASGRAPH_MCP_TOKEN` | *(unset)* | Bearer token required by the HTTP transport. |
| `VERITASGRAPH_MCP_ALLOWED_ORIGINS` | *(unset)* | Comma-separated browser origins allowed in addition to loopback. |
| `VERITASGRAPH_MCP_MAX_BODY` | `10485760` | Largest accepted HTTP request body, in bytes. |

---

## Use it through VeritasGraph Studio

The same tools and resources are exposed over HTTP by the Studio backend, so you
can drive the MCP server without an IDE — and the Studio agent pipeline can call
its tools directly.

Start the Studio API and the bridge mounts under `/mcp`:

```bash
uvicorn studio_api.main:app --port 8200
```

The bridge uses Studio auth (`Authorization: Bearer <token>` from
`STUDIO_API_TOKENS`). Tools are tiered **read / write / admin**: a viewer token
sees read tools, an editor also gets ingest/import/propose, and admin tools
(`veritasgraph_clear_graph`) appear only when `VERITASGRAPH_MCP_MODE=admin`.
The stdio server honours the same `VERITASGRAPH_MCP_MODE` (default `write`;
use `read` for untrusted clients). Hidden tools return JSON-RPC `-32601`.

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

## Register in your client

All examples run the PyPI package with `uvx`. To run from a clone instead, use
`"command": "/abs/path/to/VeritasGraph/.venv/bin/python"` with
`"args": ["-m", "veritasgraph_mcp"]`.

### Claude Code

```bash
claude mcp add veritasgraph -e VERITASGRAPH_MODEL=qwen3:latest -- uvx veritasgraph-mcp
```

### Claude Desktop

Download `veritasgraph-mcp-<version>.mcpb` from the
[latest release](https://github.com/bibinprathap/VeritasGraph/releases/latest) and
open it, or add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "veritasgraph": {
      "command": "uvx",
      "args": ["veritasgraph-mcp"],
      "env": { "VERITASGRAPH_MODEL": "qwen3:latest" }
    }
  }
}
```

The same `mcpServers` block works for **Cursor** (`~/.cursor/mcp.json`),
**Windsurf** (`~/.codeium/windsurf/mcp_config.json`) and **Cline**
(`cline_mcp_settings.json`).

### VS Code — `.vscode/mcp.json`

```json
{
  "servers": {
    "veritasgraph": {
      "type": "stdio",
      "command": "uvx",
      "args": ["veritasgraph-mcp"]
    }
  }
}
```

Or run `code --add-mcp '{"name":"veritasgraph","command":"uvx","args":["veritasgraph-mcp"]}'`.

### OpenAI Codex CLI — `~/.codex/config.toml`

```toml
[mcp_servers.veritasgraph]
command = "uvx"
args = ["veritasgraph-mcp"]
```

### Gemini CLI — `~/.gemini/settings.json`

```json
{
  "mcpServers": {
    "veritasgraph": { "command": "uvx", "args": ["veritasgraph-mcp"] }
  }
}
```

### Continue — `~/.continue/config.yaml`

```yaml
mcpServers:
  - name: veritasgraph
    command: uvx
    args: ["veritasgraph-mcp"]
```

### Docker (any client)

```json
{
  "mcpServers": {
    "veritasgraph": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-v", "veritasgraph:/data",
               "-e", "OLLAMA_HOST=host.docker.internal:11434",
               "ghcr.io/bibinprathap/veritasgraph-mcp"]
    }
  }
}
```

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
[`studio_api/graphrag_engine.py`](https://github.com/bibinprathap/VeritasGraph/blob/restored-main/studio_api/graphrag_engine.py), the same
engine that powers Studio. That means the MCP surface, the Studio UI, and the
HTTP API all read and write the **same** local knowledge graph.

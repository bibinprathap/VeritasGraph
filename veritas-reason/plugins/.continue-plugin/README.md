# VeritasReason — Continue Plugin

> **v0.4.0** — Adds VeritasReason as an MCP server and context provider to [Continue.dev](https://continue.dev).

## MCP Server Setup

Add to `~/.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "veritasreason",
      "command": "python",
      "args": ["-m", "veritasreason.mcp_server"]
    }
  ]
}
```

Continue will show all 17 VeritasReason skills in the `@veritasreason` context provider dropdown.

## Knowledge Explorer

```bash
veritasreason-explorer --graph my_graph.json --port 8000
```

Open `http://localhost:5174` for the interactive graph dashboard.

## Requirements

- Python 3.10+
- `pip install veritas-reason`

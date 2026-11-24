# Changelog

All notable changes to the `veritasgraph-mcp` package are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0]

### Added
- Protocol version negotiation. The server supports MCP 2025-11-25, 2025-06-18, 2025-03-26 and 2024-11-05.
- Every tool now has a `title` and `annotations` (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`).
- `outputSchema` for `veritasgraph_check_answerable` and `veritasgraph_query`. Dict results are also returned as `structuredContent`.
- Prompts: `grounded_answer`, `verify_claim` and `explore_entity` (`prompts/list`, `prompts/get`).
- Streamable HTTP transport: `veritasgraph-mcp --transport http`. It checks the Origin header, supports an optional bearer token (`VERITASGRAPH_MCP_TOKEN`) and limits request size.
- `--version` flag, a server `title` and icons in `serverInfo`.
- Docker image on GHCR, an MCPB bundle for Claude Desktop, and listing files for Glama, Smithery and Cline.

### Changed
- An exception inside a tool is now returned as a tool result with `isError: true`, so the model can see the error. Unknown tools still return JSON-RPC error `-32601`.
- Installed copies (pip, uvx, MCPB) store the graph in `~/.veritasgraph` when neither `STUDIO_DATA_DIR` nor `VERITASGRAPH_DB` is set.
- The Docker image runs as a non-root user and serves HTTP when `PORT` is set.

## [0.2.0]

- First release in the official MCP Registry as `io.github.bibinprathap/veritasgraph`.

# VeritasGraph MCP Server — Glama-compatible container image.
#
# The MCP server speaks JSON-RPC 2.0 over stdio. Schema discovery
# (`initialize` / `tools/list`) uses lazy imports, so the server starts and
# responds to introspection with only the Python standard library — no Ollama,
# graph store, or heavy runtime required. This keeps the image small and makes
# Glama's start-and-introspect check fast and reliable.
#
# Build:  docker build -f veritasgraph_mcp/Dockerfile -t veritasgraph-mcp .
# Run:    docker run --rm -i veritasgraph-mcp                    (stdio)
#         docker run --rm -e PORT=8765 -p 8765:8765 veritasgraph-mcp   (Streamable HTTP at /mcp)

FROM python:3.12-slim

LABEL io.modelcontextprotocol.server.name="io.github.bibinprathap/veritasgraph" \
      org.opencontainers.image.source="https://github.com/bibinprathap/VeritasGraph" \
      org.opencontainers.image.description="Zero-trust GraphRAG MCP server with citation-grounded answers" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy only what the MCP server needs to build and run.
COPY pyproject.toml README.md ./
COPY veritasgraph_mcp/ ./veritasgraph_mcp/
COPY studio_api/ ./studio_api/
COPY veritasgraph/ ./veritasgraph/

# Install the package (declares its single runtime dep: httpx).
RUN pip install --upgrade pip && pip install . \
    && useradd --system --uid 10001 --home-dir /data veritas \
    && mkdir -p /data && chown veritas /data

# Graph store lives on a volume; default to read-only tools for untrusted clients.
ENV STUDIO_DATA_DIR=/data \
    VERITASGRAPH_MCP_MODE=read
VOLUME ["/data"]
USER veritas

# stdio by default (Glama connects here and issues `initialize` / `tools/list`).
# Hosting platforms that set PORT (Smithery, Cloud Run, ...) get Streamable HTTP.
ENTRYPOINT ["/bin/sh", "-c", "if [ -n \"$PORT\" ]; then exec python -m veritasgraph_mcp --transport http --host 0.0.0.0 --port \"$PORT\" \"$@\"; else exec python -m veritasgraph_mcp \"$@\"; fi", "--"]

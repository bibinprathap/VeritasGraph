# VeritasGraph MCP Server — Glama-compatible container image.
#
# The MCP server speaks JSON-RPC 2.0 over stdio. Schema discovery
# (`initialize` / `tools/list`) uses lazy imports, so the server starts and
# responds to introspection with only the Python standard library — no Ollama,
# graph store, or heavy runtime required. This keeps the image small and makes
# Glama's start-and-introspect check fast and reliable.
#
# Build:  docker build -f veritasgraph_mcp/Dockerfile -t veritasgraph-mcp .
# Run:    docker run --rm -i veritasgraph-mcp

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy only what the MCP server needs to build and run.
COPY pyproject.toml README.md ./
COPY veritasgraph_mcp/ ./veritasgraph_mcp/
COPY studio_api/ ./studio_api/

# Install the package (declares its single runtime dep: httpx).
RUN pip install --upgrade pip && pip install .

# stdio MCP server — Glama connects here and issues `initialize` / `tools/list`.
ENTRYPOINT ["python", "-m", "veritasgraph_mcp"]

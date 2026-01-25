# VeritasGraph MCP Server Dockerfile
# Multi-stage build for smaller image size

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build && \
    pip install --no-cache-dir \
    mcp>=1.0.0 \
    fastmcp>=0.1.0 \
    pydantic>=2.0.0 \
    python-dotenv>=1.0.0 \
    graphrag>=0.3.0 \
    tiktoken>=0.5.0 \
    pandas>=2.0.0 \
    pyarrow>=14.0.0 \
    lancedb>=0.4.0 \
    trafilatura>=1.6.0 \
    youtube-transcript-api>=0.6.0

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY veritas_mcp_server.py .
COPY .env.example .env

# Create directories for mounting
RUN mkdir -p /app/graphrag-config/input \
    && mkdir -p /app/graphrag-config/output/artifacts

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV VERITAS_OUTPUT_DIR=/app/graphrag-config/output/artifacts
ENV VERITAS_INPUT_DIR=/app/graphrag-config/input

# Expose SSE port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command - SSE transport for container use
ENTRYPOINT ["python", "veritas_mcp_server.py"]
CMD ["--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]

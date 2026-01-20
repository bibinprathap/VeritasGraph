# Power BI Natural Language Query Backend

Backend API that converts natural language queries to DAX and executes them against Power BI using MCP tools.

## Architecture

- **FastAPI**: REST API framework
- **LangChain + LangGraph**: Agent framework for natural language processing
- **MCP Client**: Connects to Power BI MCP Server
- **LLM Provider**: Abstraction for Ollama (local) and OpenAI-compatible endpoints (production)

## Setup

### 1. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Configure Environment Variables

Add these variables to your existing `.env` file in the **project root** (same level as `src/` and `backend/`):

```env
# LLM Provider (ollama or openai)
LLM_PROVIDER=ollama

# Ollama Settings (for local development)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# OpenAI-Compatible Settings (for production)
# OPENAI_API_KEY=your_api_key_here
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_MODEL=gpt-4

# API Settings
DEBUG=true
LOG_LEVEL=INFO
TEMPERATURE=0.1
MAX_ITERATIONS=15
```

**Note:** The backend reads from the `.env` file at the project root (same location used by the MCP server).

### 3. Start Ollama (for local development)

```bash
# Make sure Ollama is running
ollama serve

# Pull the model
ollama pull llama3.2:3b
```

### 4. Run the Backend

```bash
# From project root
python -m backend.app

# Or using uvicorn directly
uvicorn backend.app:app --reload --port 8000
```

## API Endpoints

### POST `/api/v1/query`

Convert natural language query to DAX and execute it.

**Request:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "query": "Show me the total sales by region for the last quarter",
  "workspace_id": "3fae44c2-94db-4d3b-8f39-f64b937a5d10",
  "dataset_id": "1e50eb69-ffac-4f25-8fac-57a289e5e6d6"
}
```

**Response:**
```json
{
  "dax_query": "EVALUATE SUMMARIZECOLUMNS(...)",
  "natural_language_query": "Show me the total sales by region for the last quarter",
  "result": [
    {"Region": "North", "Total Sales": 150000},
    {"Region": "South", "Total Sales": 200000}
  ],
  "error": null,
  "metadata": {
    "workspace_id": "...",
    "dataset_id": "..."
  }
}
```

### GET `/api/v1/health`

Health check endpoint.

### GET `/api/v1/tools`

List available MCP tools.

## How It Works

1. **User sends natural language query** → API receives request with access token
2. **Agent explores dataset structure** → Uses MCP tools to list tables/columns
3. **Agent generates DAX query** → LLM converts natural language to DAX
4. **Agent executes DAX** → Uses MCP `execute_dax` tool
5. **Results returned** → JSON response with query and results

## LLM Provider Configuration

### Local Development (Ollama)

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

### Production (OpenAI-Compatible)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

Or use any OpenAI-compatible endpoint:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://your-endpoint.com/v1
OPENAI_MODEL=your-model
```

## Project Structure

```
backend/
├── app.py                 # FastAPI application
├── config.py              # Configuration management
├── mcp_client.py          # MCP client wrapper
├── llm_provider.py        # LLM provider abstraction
├── agents/
│   └── powerbi_agent.py   # LangGraph agent
├── api/
│   └── routes.py          # API routes
├── models/
│   ├── requests.py        # Request models
│   └── responses.py       # Response models
└── utils/
    └── logger.py          # Logging setup
```

## Testing

```bash
# Test with curl
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "your_token",
    "query": "Show me all tables",
    "workspace_id": "...",
    "dataset_id": "..."
  }'
```

## Notes

- The MCP server must be accessible (runs via stdio)
- Access tokens are required for all Power BI operations
- The agent uses LangGraph for multi-step reasoning
- Temperature is set low (0.1) for deterministic DAX generation


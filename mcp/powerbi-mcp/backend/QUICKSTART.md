# Quick Start Guide

## Prerequisites

1. **Python 3.10+** installed
2. **Ollama** installed and running (for local development)
3. **Power BI access token** (for testing)

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Start Ollama (Local Development)

```bash
# Start Ollama service
ollama serve

# Pull a model (in another terminal)
ollama pull llama3.2:3b
```

### 3. Configure Environment

Add these variables to your existing `.env` file in the **project root**:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
DEBUG=true
```

**Note:** The backend uses the same `.env` file as the MCP server (at project root).

### 4. Run the Backend

```bash
# From project root
python -m backend.app

# Or with uvicorn
uvicorn backend.app:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

## Test the API

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Natural Language Query

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "your_powerbi_token",
    "query": "Show me all tables in the dataset",
    "workspace_id": "3fae44c2-94db-4d3b-8f39-f64b937a5d10",
    "dataset_id": "1e50eb69-ffac-4f25-8fac-57a289e5e6d6"
  }'
```

## Production Setup

For production, switch to OpenAI-compatible endpoint:

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

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`


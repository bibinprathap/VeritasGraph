# OpenAI-Compatible API Support

VeritasGraph now supports **any OpenAI-compatible API**, making it easy to use with various LLM providers including:

- **OpenAI** (Native)
- **Azure OpenAI**
- **Groq**
- **Together AI**
- **OpenRouter**
- **Anyscale**
- **LM Studio** (Local)
- **LocalAI** (Local)
- **vLLM** (Local/Server)
- **Ollama** (Local)
- **Any other OpenAI-compatible endpoint**

## Quick Start

### 1. Choose Your Configuration File

Copy the appropriate example configuration:

```bash
# For OpenAI-compatible APIs (OpenAI, Groq, Together, etc.)
cp settings_openai.yaml settings.yaml
cp .env.openai.example .env

# For Ollama (default local setup)
# Keep existing settings.yaml
```

### 2. Configure Environment Variables

Edit your `.env` file with your provider's settings:

```bash
# Required
GRAPHRAG_API_KEY=your-api-key-here

# LLM Configuration
GRAPHRAG_LLM_MODEL=gpt-4-turbo-preview
GRAPHRAG_LLM_API_BASE=https://api.openai.com/v1

# Embedding Configuration
GRAPHRAG_EMBEDDING_MODEL=text-embedding-3-small
GRAPHRAG_EMBEDDING_API_BASE=https://api.openai.com/v1
```

### 3. Run GraphRAG

```bash
# Index your documents
python -m graphrag.index --root .

# Launch the UI
python app.py
```

## Provider-Specific Configuration

### OpenAI (Native)

```env
GRAPHRAG_API_KEY=sk-your-openai-api-key
GRAPHRAG_LLM_MODEL=gpt-4-turbo-preview
GRAPHRAG_LLM_API_BASE=https://api.openai.com/v1
GRAPHRAG_EMBEDDING_MODEL=text-embedding-3-small
GRAPHRAG_EMBEDDING_API_BASE=https://api.openai.com/v1
```

### Azure OpenAI

```env
GRAPHRAG_API_KEY=your-azure-key
GRAPHRAG_API_TYPE=azure
GRAPHRAG_API_VERSION=2024-02-15-preview
GRAPHRAG_LLM_MODEL=gpt-4
GRAPHRAG_LLM_API_BASE=https://your-resource.openai.azure.com
GRAPHRAG_DEPLOYMENT_NAME=your-deployment-name
GRAPHRAG_EMBEDDING_MODEL=text-embedding-ada-002
GRAPHRAG_EMBEDDING_API_BASE=https://your-resource.openai.azure.com
GRAPHRAG_EMBEDDING_DEPLOYMENT_NAME=your-embedding-deployment
```

### Groq

```env
GRAPHRAG_API_KEY=gsk_your-groq-key
GRAPHRAG_LLM_MODEL=llama-3.1-70b-versatile
GRAPHRAG_LLM_API_BASE=https://api.groq.com/openai/v1
# Groq doesn't support embeddings, use Ollama locally
GRAPHRAG_EMBEDDING_MODEL=nomic-embed-text
GRAPHRAG_EMBEDDING_API_BASE=http://localhost:11434/v1
```

### Together AI

```env
GRAPHRAG_API_KEY=your-together-key
GRAPHRAG_LLM_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
GRAPHRAG_LLM_API_BASE=https://api.together.xyz/v1
GRAPHRAG_EMBEDDING_MODEL=togethercomputer/m2-bert-80M-8k-retrieval
GRAPHRAG_EMBEDDING_API_BASE=https://api.together.xyz/v1
```

### OpenRouter

```env
GRAPHRAG_API_KEY=sk-or-your-openrouter-key
GRAPHRAG_LLM_MODEL=anthropic/claude-3.5-sonnet
GRAPHRAG_LLM_API_BASE=https://openrouter.ai/api/v1
# OpenRouter can proxy embedding models too
GRAPHRAG_EMBEDDING_MODEL=openai/text-embedding-3-small
GRAPHRAG_EMBEDDING_API_BASE=https://openrouter.ai/api/v1
```

### LM Studio (Local)

```env
GRAPHRAG_API_KEY=lm-studio
GRAPHRAG_LLM_MODEL=local-model
GRAPHRAG_LLM_API_BASE=http://localhost:1234/v1
# Use Ollama for embeddings
GRAPHRAG_EMBEDDING_MODEL=nomic-embed-text
GRAPHRAG_EMBEDDING_API_BASE=http://localhost:11434/v1
```

### vLLM Server

```env
GRAPHRAG_API_KEY=vllm
GRAPHRAG_LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
GRAPHRAG_LLM_API_BASE=http://localhost:8000/v1
GRAPHRAG_EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
GRAPHRAG_EMBEDDING_API_BASE=http://localhost:8001/v1
```

### LocalAI

```env
GRAPHRAG_API_KEY=localai
GRAPHRAG_LLM_MODEL=gpt-4
GRAPHRAG_LLM_API_BASE=http://localhost:8080/v1
GRAPHRAG_EMBEDDING_MODEL=text-embedding-ada-002
GRAPHRAG_EMBEDDING_API_BASE=http://localhost:8080/v1
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GRAPHRAG_API_KEY` | API key for authentication | `sk-...` |
| `GRAPHRAG_LLM_MODEL` | Model name for chat/completion | `gpt-4-turbo-preview` |
| `GRAPHRAG_LLM_API_BASE` | Base URL for LLM API | `https://api.openai.com/v1` |
| `GRAPHRAG_EMBEDDING_MODEL` | Model name for embeddings | `text-embedding-3-small` |
| `GRAPHRAG_EMBEDDING_API_BASE` | Base URL for embedding API | `https://api.openai.com/v1` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GRAPHRAG_API_TYPE` | API type (`openai` or `azure`) | `openai` |
| `GRAPHRAG_API_VERSION` | Azure API version | `2024-02-15-preview` |
| `GRAPHRAG_DEPLOYMENT_NAME` | Azure deployment name | Same as model |
| `GRAPHRAG_EMBEDDING_API_KEY` | Separate key for embeddings | Same as `GRAPHRAG_API_KEY` |
| `GRAPHRAG_EMBEDDING_API_TYPE` | Embedding API type | Same as `GRAPHRAG_API_TYPE` |
| `GRAPHRAG_EMBEDDING_DEPLOYMENT_NAME` | Azure embedding deployment | Same as embedding model |
| `GRAPHRAG_MAX_RETRIES` | Max API retry attempts | `10` |
| `GRAPHRAG_ORGANIZATION` | OpenAI organization ID | None |

## Hybrid Configurations

You can mix different providers for LLM and embeddings:

### Groq LLM + Ollama Embeddings

```env
GRAPHRAG_API_KEY=gsk_your-groq-key
GRAPHRAG_LLM_MODEL=llama-3.1-70b-versatile
GRAPHRAG_LLM_API_BASE=https://api.groq.com/openai/v1
GRAPHRAG_EMBEDDING_API_KEY=ollama
GRAPHRAG_EMBEDDING_MODEL=nomic-embed-text
GRAPHRAG_EMBEDDING_API_BASE=http://localhost:11434/v1
```

### OpenAI LLM + Local Embeddings (vLLM)

```env
GRAPHRAG_API_KEY=sk-your-openai-key
GRAPHRAG_LLM_MODEL=gpt-4-turbo-preview
GRAPHRAG_LLM_API_BASE=https://api.openai.com/v1
GRAPHRAG_EMBEDDING_API_KEY=vllm
GRAPHRAG_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
GRAPHRAG_EMBEDDING_API_BASE=http://localhost:8001/v1
```

## Docker Configuration

When using Docker Compose, pass environment variables:

```yaml
services:
  app:
    environment:
      - GRAPHRAG_API_KEY=${GRAPHRAG_API_KEY}
      - GRAPHRAG_LLM_MODEL=${GRAPHRAG_LLM_MODEL}
      - GRAPHRAG_LLM_API_BASE=${GRAPHRAG_LLM_API_BASE}
      - GRAPHRAG_EMBEDDING_MODEL=${GRAPHRAG_EMBEDDING_MODEL}
      - GRAPHRAG_EMBEDDING_API_BASE=${GRAPHRAG_EMBEDDING_API_BASE}
      - GRAPHRAG_API_TYPE=${GRAPHRAG_API_TYPE:-openai}
```

## Troubleshooting

### Common Issues

1. **API Key Invalid**
   - Verify your API key is correct
   - Check if the key has the required permissions

2. **Model Not Found**
   - Verify the model name matches your provider's naming convention
   - For Azure, ensure the deployment name is correct

3. **Connection Refused**
   - Check if the API base URL is correct
   - For local servers, ensure they're running

4. **Rate Limiting**
   - Adjust `GRAPHRAG_MAX_RETRIES`
   - Add rate limiting in `settings.yaml`

### Testing Your Configuration

```python
# Quick test script
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["GRAPHRAG_API_KEY"],
    base_url=os.environ["GRAPHRAG_LLM_API_BASE"]
)

response = client.chat.completions.create(
    model=os.environ["GRAPHRAG_LLM_MODEL"],
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## Migration from Ollama-Only Setup

If you're migrating from the Ollama-only configuration:

1. **Backup your current settings:**
   ```bash
   cp settings.yaml settings_ollama_backup.yaml
   cp .env .env.ollama.backup
   ```

2. **Update configuration:**
   ```bash
   cp settings_openai.yaml settings.yaml
   ```

3. **Set environment variables** for your new provider

4. **Re-index if changing embedding models:**
   ```bash
   # Clear cache and output
   rm -rf cache output
   
   # Re-index
   python -m graphrag.index --root .
   ```

Note: If you change embedding models, you **must** re-index your documents as embeddings are model-specific.

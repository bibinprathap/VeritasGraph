# LLM Providers Module

The `veritasreason.llms` module provides a unified interface for LLM providers, supporting Groq, OpenAI, HuggingFace, and LiteLLM (100+ LLMs) with clean imports and consistent API.

## Overview

The **LLM Providers Module** provides a unified interface for Large Language Model (LLM) providers. It abstracts away provider-specific details, enabling you to switch between different LLM providers without changing your code.

### What is the LLM Providers Module?

The LLM Providers module provides:

- **Unified LLM APIs**: Single interface for Groq, OpenAI, HuggingFace, and LiteLLM (100+ models)
- **Easy Provider Switching**: Change providers without code changes
- **Multiple Model Support**: Access to 100+ LLMs through LiteLLM
- **GraphRAG Integration**: Seamless integration with GraphRAG reasoning features
- **Structured Output**: Generate structured data with robust JSON parsing and automatic retries (3 attempts).

### Why Use the LLM Providers Module?

- **Flexibility**: Switch between providers based on cost, speed, or capability
- **Consistency**: Same API regardless of provider
- **Local Models**: Support for local HuggingFace models
- **Fast Inference**: Groq for ultra-fast inference
- **Enterprise Models**: Access to OpenAI, Anthropic, and other enterprise providers

### How It Works

The LLM Providers module follows a simple workflow:

1. **Provider Selection**: Choose a provider (Groq, OpenAI, HuggingFace, LiteLLM)
2. **Model Configuration**: Configure model name, API keys, and parameters
3. **Text Generation**: Generate text using a consistent API
4. **Structured Output**: Optionally generate structured data (JSON, entities, etc.)

## Quick Start

```python
from veritasreason.llms import Groq, OpenAI, HuggingFaceLLM, LiteLLM
import os

# Groq - Fast inference
groq = Groq(model="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))
response = groq.generate("What is AI?")

# OpenAI
openai = OpenAI(model="gpt-4", api_key=os.getenv("OPENAI_API_KEY"))
response = openai.generate("What is AI?")

# HuggingFace - Local models
hf = HuggingFaceLLM(model_name="gpt2")  # or model="gpt2"
response = hf.generate("What is AI?")

# LiteLLM - Unified interface to 100+ LLMs
litellm = LiteLLM(model="openai/gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
response = litellm.generate("What is AI?")
```

## Providers

### Groq

Fast inference provider using Groq's API.

```python
from veritasreason.llms import Groq

groq = Groq(
    model="llama-3.1-8b-instant",
    api_key="your-api-key"  # or use GROQ_API_KEY env var
)

response = groq.generate("Hello, world!")
structured = groq.generate_structured("Extract entities from: Apple Inc.")
```

**Parameters:**
- `model` (str): Model name (default: "llama-3.1-8b-instant")
- `api_key` (str, optional): Groq API key (default: from GROQ_API_KEY env var)
- `**kwargs`: Additional provider options

**Methods:**
- `generate(prompt: str, **kwargs) -> str`: Generate text from prompt
- `generate_structured(prompt: str, **kwargs) -> Dict[str, Any]`: Generate structured JSON output
- `is_available() -> bool`: Check if provider is available

### OpenAI

OpenAI API provider for GPT models.

```python
from veritasreason.llms import OpenAI

openai = OpenAI(
    model="gpt-4",
    api_key="your-api-key"  # or use OPENAI_API_KEY env var
)

response = openai.generate("Hello, world!")
```

**Parameters:**
- `model` (str): Model name (default: "gpt-3.5-turbo")
- `api_key` (str, optional): OpenAI API key (default: from OPENAI_API_KEY env var)
- `**kwargs`: Additional provider options

**Methods:**
- `generate(prompt: str, **kwargs) -> str`: Generate text from prompt
- `generate_structured(prompt: str, **kwargs) -> Dict[str, Any]`: Generate structured JSON output
- `is_available() -> bool`: Check if provider is available

### HuggingFaceLLM

Local LLM inference using HuggingFace Transformers.

```python
from veritasreason.llms import HuggingFaceLLM

hf = HuggingFaceLLM(
    model_name="gpt2",
    device="cuda"  # or "cpu", default: auto-detect
)

response = hf.generate("Hello, world!")
```

**Parameters:**
- `model_name` (str, optional): HuggingFace model name (default: "gpt2")
- `model` (str, optional): Alias for model_name (for consistency with other providers)
- `device` (str, optional): Device to use ("cuda" or "cpu", default: auto-detect)
- `**kwargs`: Additional provider options

**Note:** Both `model` and `model_name` are supported for consistency with other providers.

**Methods:**
- `generate(prompt: str, **kwargs) -> str`: Generate text from prompt
- `generate_structured(prompt: str, **kwargs) -> Dict[str, Any]`: Generate structured JSON output
- `is_available() -> bool`: Check if provider is available

### LiteLLM

Unified interface to 100+ LLM providers via LiteLLM library.

```python
from veritasreason.llms import LiteLLM

# Use any provider via LiteLLM
litellm = LiteLLM(
    model="openai/gpt-4o",  # Provider/model format
    api_key=os.getenv("OPENAI_API_KEY")
)

# Or use other providers
litellm = LiteLLM(model="anthropic/claude-sonnet-4-20250514")
litellm = LiteLLM(model="groq/llama-3.1-8b-instant")
litellm = LiteLLM(model="azure/gpt-4")

response = litellm.generate("Hello, world!")
```

**Parameters:**
- `model` (str): Model identifier in format "provider/model-name"
  - Examples: "openai/gpt-4o", "anthropic/claude-sonnet-4-20250514", "groq/llama-3.1-8b-instant", "azure/gpt-4"
- `api_key` (str, optional): API key (can use environment variables)
- `**kwargs`: Additional LiteLLM options (temperature, max_tokens, etc.)

**Methods:**
- `generate(prompt: str, **kwargs) -> str`: Generate text from prompt
- `generate_structured(prompt: str, **kwargs) -> Dict[str, Any]`: Generate structured JSON output
- `is_available() -> bool`: Check if provider is available

**Supported Providers:**
- OpenAI, Anthropic, Groq, Azure, Bedrock, Vertex AI, Cohere, Mistral, and 90+ more
- See [LiteLLM Documentation](https://docs.litellm.ai/) for full list

## Integration with GraphRAG

The LLM providers integrate seamlessly with GraphRAG reasoning:

```python
from veritasreason.context import AgentContext
from veritasreason.llms import Groq
from veritasreason.vector_store import VectorStore
import os

context = AgentContext(
    vector_store=VectorStore(backend="faiss"),
    knowledge_graph=kg
)

llm_provider = Groq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY")
)

result = context.query_with_reasoning(
    query="What IPs are associated with security alerts?",
    llm_provider=llm_provider,
    max_hops=2
)

print(f"Response: {result['response']}")
print(f"Reasoning Path: {result['reasoning_path']}")
```

## Common Parameters

All providers support common generation parameters:

- `temperature` (float): Sampling temperature (0.0-2.0)
- `max_tokens` (int): Maximum tokens to generate
- `top_p` (float): Nucleus sampling parameter
- `frequency_penalty` (float): Frequency penalty
- `presence_penalty` (float): Presence penalty

Example:

```python
response = groq.generate(
    "What is AI?",
    temperature=0.7,
    max_tokens=500,
    top_p=0.9
)
```

## Error Handling

All providers gracefully handle errors:

```python
try:
    response = groq.generate("Hello")
except ProcessingError as e:
    print(f"Generation failed: {e}")
```

If a provider is not available (library not installed, API key missing), a `ProcessingError` is raised with a helpful message.

### Built-in Retries
The `generate_structured` method includes built-in retry logic for all providers:
- **Attempts**: 3
- **Wait Time**: 1 second base with exponential backoff
- **Triggers**: Network errors, rate limits, and malformed JSON responses.

### Robust JSON Parsing
`BaseProvider` uses an enhanced `_parse_json` method that can handle:
- Markdown code blocks (e.g., ```json ... ```)
- Extra text before or after the JSON object
- Common LLM formatting inconsistencies.

## Examples

### Basic Text Generation

```python
from veritasreason.llms import Groq

groq = Groq(model="llama-3.1-8b-instant")
response = groq.generate("Explain quantum computing in simple terms.")
print(response)
```

### Structured Output

```python
from veritasreason.llms import OpenAI

openai = OpenAI(model="gpt-4")
result = openai.generate_structured(
    "Extract entities from: Apple Inc. was founded by Steve Jobs in 1976."
)
# Returns: {"entities": [{"name": "Apple Inc.", "type": "Organization"}, ...]}
```

### Using LiteLLM for Multiple Providers

```python
from veritasreason.llms import LiteLLM

# Switch between providers easily
providers = [
    LiteLLM(model="openai/gpt-4o"),
    LiteLLM(model="anthropic/claude-sonnet-4-20250514"),
    LiteLLM(model="groq/llama-3.1-8b-instant")
]

for provider in providers:
    response = provider.generate("What is AI?")
    print(f"{provider.model}: {response[:50]}...")
```

## Installation

Most providers require additional dependencies:

```bash
# Groq
pip install groq

# OpenAI
pip install openai

# HuggingFace
pip install transformers torch

# LiteLLM (supports 100+ providers)
pip install litellm
```

## Cookbook

Interactive tutorials that use LLM providers:

- **[Advanced Extraction](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/advanced/01_Advanced_Extraction.ipynb)**: Custom extractors and LLM-based extraction
  - **Topics**: LLM extraction, custom models, complex pattern matching
  - **Difficulty**: Advanced
  - **Use Cases**: Domain-specific extraction, complex schemas

- **[GraphRAG Complete](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/use_cases/advanced_rag/01_GraphRAG_Complete.ipynb)**: Production-ready GraphRAG system using LLMs
  - **Topics**: GraphRAG, LLM integration, hybrid retrieval
  - **Difficulty**: Advanced
  - **Use Cases**: Building AI applications with knowledge graphs

## See Also

- [Context Module](context.md) - GraphRAG with multi-hop reasoning
- [Semantic Extract Module](semantic_extract.md) - Entity and relationship extraction
- [GraphRAG Cookbook](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/use_cases/advanced_rag/01_GraphRAG_Complete.ipynb) - Complete GraphRAG example


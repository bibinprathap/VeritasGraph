# Embeddings Module Reference

> **Text embedding generation with multiple model support.**

---

## 🎯 System Overview

The **Embeddings Module** provides a unified interface for generating vector representations of text. It abstracts away the complexity of different providers (OpenAI, HuggingFace, FastEmbed) and ensures consistent formatting for vector databases.

### What are Embeddings?

**Embeddings** are numerical representations of text that capture semantic meaning. They convert words, sentences, or documents into dense vectors (arrays of numbers) in a high-dimensional space. Similar texts have similar vectors, enabling semantic search, similarity matching, and machine learning applications.

### Why Use the Embeddings Module?

- **Unified Interface**: Switch between different embedding providers without changing your code
- **Consistent Formatting**: All embeddings are normalized and formatted consistently for vector databases
- **Performance**: Optimized batch processing for high-throughput embedding generation
- **Flexibility**: Support for local models (FastEmbed, Sentence Transformers) and API-based models (OpenAI, Anthropic)
- **Vector DB Ready**: Automatic formatting for FAISS, Qdrant, Weaviate, and Milvus

### How It Works

The embeddings module uses a provider-based architecture:

1. **EmbeddingGenerator**: Main orchestrator that manages the active model
2. **Provider Stores**: Backend implementations for each provider (FastEmbed, OpenAI, etc.)
3. **TextEmbedder**: Simplified interface focused on text-to-vector operations
4. **VectorEmbeddingManager**: Prepares embeddings for specific vector database formats

### Key Capabilities

<div class="grid cards" markdown>

-   :material-power-plug:{ .lg .middle } **Multi-Provider Support**

    ---

    Seamlessly switch between Sentence Transformers, FastEmbed, OpenAI, and BGE models.

-   :material-api:{ .lg .middle } **Unified Interface**

    ---

    Single API for all embedding backends with consistent normalization and output formatting.

-   :material-rocket-launch:{ .lg .middle } **Efficient Batching**

    ---

    Optimized batch processing and pooling strategies for high-throughput embedding generation.

-   :material-database-check:{ .lg .middle } **Vector DB Ready**

    ---

    Automatic formatting and validation for FAISS, Qdrant, and Weaviate.

</div>

!!! tip "When to Use"
    - **Vectorization**: Converting text to embeddings for storage.
    - **Semantic Comparison**: Calculating similarity between two text snippets.
    - **Model Abstraction**: Switching between local and API-based models without code changes.

---

## 🏗️ Architecture Components

### EmbeddingGenerator (The Orchestrator)
The main entry point for generating embeddings. It manages the active model and routes requests to the appropriate provider store.

#### **Constructor Parameters**
*   `method` (Default: `"fastembed"`): The embedding provider to use (e.g., `"sentence_transformers"`, `"openai"`, `"fastembed"`).
*   `model_name` (Optional): Specific model name (e.g., `"all-MiniLM-L6-v2"`, `"text-embedding-3-small"`).
*   `device` (Default: `"cpu"`): Computing device (`"cpu"`, `"cuda"`, `"mps"`).
*   `normalize` (Default: `True`): Whether to L2-normalize embeddings (crucial for cosine similarity).

#### **Core Methods**

| Method | Description |
|--------|-------------|
| `` `generate_embeddings(data, data_type="text")` `` | Generates an embedding for a single item |
| `` `process_batch(items)` `` | Generates embeddings for a list of items (optimized) |
| `` `compare_embeddings(emb1, emb2)` `` | Calculates cosine similarity between two vectors |
| `` `get_text_method()` `` | Returns the active embedding strategy |
| `set_text_model(method, model_name, **config)` | Dynamically switches the text embedding model. |

#### **Code Example**
```python
from veritasreason.embeddings import EmbeddingGenerator

# 1. Initialize
gen = EmbeddingGenerator(
    method="sentence_transformers",
    model_name="all-MiniLM-L6-v2"
)

# 2. Generate
vector = gen.generate_embeddings("Hello world")

# 3. Compare
vec1 = gen.generate_embeddings("AI is great")
vec2 = gen.generate_embeddings("Machine learning is awesome")
similarity = gen.compare_embeddings(vec1, vec2)
print(f"Similarity: {similarity}")
```

---

### TextEmbedder (The Worker)
A specialized class focused purely on text-to-vector operations. It wraps the `EmbeddingGenerator` with text-specific logic and simplified methods.

#### **Core Methods**

| Method | Description |
|--------|-------------|
| `` `embed_text(text)` `` | Returns a list of floats for the input string |
| `` `embed_batch(texts)` `` | Returns a list of lists (vectors) for the input strings |
| `` `get_embedding_dimension()` `` | Returns the size of the output vector (e.g., 384, 768, 1536) |
| `` `set_model(method, model_name, **config)` `` | Switches the underlying embedding model |
| `` `get_method()` `` | Returns the current method name |
| `` `get_model_info()` `` | Returns details about the current model |

#### **Code Example**
```python
from veritasreason.embeddings import TextEmbedder

# Initialize with FastEmbed (lightweight, fast)
embedder = TextEmbedder(method="fastembed")

# Single text
vector = embedder.embed_text("VeritasReason is powerful")

# Batch processing (Recommended for speed)
texts = ["Document 1", "Document 2", "Document 3"]
vectors = embedder.embed_batch(texts)

print(f"Dimension: {embedder.get_embedding_dimension()}")
```

---

### VectorEmbeddingManager (The Bridge)
A utility class that prepares raw embeddings for insertion into specific vector databases. It handles formatting differences between backends like FAISS and Weaviate.

#### **Core Methods**

| Method | Description |
|--------|-------------|
| `prepare_for_vector_db(embeddings, metadata, backend)` | Formats data for the target DB. |
| `validate_dimensions(embeddings, expected_dim)` | Ensures vectors match the index configuration. |
| `batch_prepare(embeddings_list)` | Prepares a batch of embeddings for storage. |

#### **Code Example**
```python
from veritasreason.embeddings import VectorEmbeddingManager, TextEmbedder

# 1. Generate Embeddings
embedder = TextEmbedder()
texts = ["Doc A", "Doc B"]
embeddings = embedder.embed_batch(texts)

# 2. Format for FAISS
manager = VectorEmbeddingManager()
formatted_data = manager.prepare_for_vector_db(
    embeddings,
    metadata=[{"id": 1, "text": "Doc A"}, {"id": 2, "text": "Doc B"}],
    backend="faiss"
)

# formatted_data is now ready to be passed to VectorStore
```

---

## ⚙️ Configuration

### Environment Variables

```bash
export EMBEDDING_MODEL=all-MiniLM-L6-v2
export EMBEDDING_DEVICE=cuda
export OPENAI_API_KEY=sk-...
```

### YAML Configuration

```yaml
embeddings:
  text:
    model: all-MiniLM-L6-v2
    method: sentence_transformers
    batch_size: 32
    normalize: true
```

---

## 🚀 Best Practices

1.  **Batch Processing**: Always use `embed_batch` or `process_batch` when dealing with multiple items. It is significantly faster, especially on GPUs.
2.  **Normalization**: Keep `normalize=True` (default) if you intend to use Cosine Similarity.
3.  **Dimension Matching**: Ensure your `VectorStore` index is created with the same dimension as your embedding model (e.g., 384 for MiniLM, 1536 for OpenAI Ada).
4.  **Caching**: Embeddings are compute-intensive. Cache results where possible to avoid re-computing vectors for the same text.

---

## 🧩 Advanced Usage

### Checking Available Providers
Dynamically check which embedding backends are installed and available.

```python
from veritasreason.embeddings import check_available_providers

providers = check_available_providers()

if providers["fastembed"]:
    print("FastEmbed is ready!")
if providers["openai"]:
    print("OpenAI embeddings are available!")
if providers["sentence_transformers"]:
    print("Sentence Transformers is installed!")

# Check all providers
for provider, available in providers.items():
    status = "✓" if available else "✗"
    print(f"{status} {provider}: {'Available' if available else 'Not installed'}")
```

This is useful for checking which embedding providers are available before initializing an embedder, especially when working in different environments.

## See Also
- [Vector Store](vector_store.md) - Stores the generated embeddings
- [Ingest](ingest.md) - Uses embeddings during processing

## Cookbook

Interactive tutorials to learn embeddings in practice:

- **[Embedding Generation](https://github.com/bibinprathap/VeritasGraph/blob/main/cookbook/introduction/12_Embedding_Generation.ipynb)**: Learn how to generate embeddings using different providers
  - **Topics**: FastEmbed, OpenAI, Sentence Transformers, batch processing, normalization
  - **Difficulty**: Intermediate
  - **Use Cases**: Understanding embedding generation, choosing the right provider

- **[Vector Store](https://github.com/bibinprathap/VeritasGraph/blob/main/cookbook/introduction/13_Vector_Store.ipynb)**: Set up and use vector stores for similarity search
  - **Topics**: FAISS, Weaviate, Qdrant, hybrid search, metadata filtering
  - **Difficulty**: Intermediate
  - **Use Cases**: Storing and searching embeddings, building RAG systems

- **[Advanced Vector Store and Search](https://github.com/bibinprathap/VeritasGraph/blob/main/cookbook/advanced/Advanced_Vector_Store_and_Search.ipynb)**: Advanced vector store operations and optimization
  - **Topics**: Index optimization, hybrid search, performance tuning, namespace management
  - **Difficulty**: Advanced
  - **Use Cases**: Production deployments, performance optimization

# Vector Store

> **Unified vector database interface supporting FAISS, Weaviate, Qdrant, Pinecone, and Milvus with Hybrid Search.**

---

## 🎯 Overview

The **Vector Store Module** provides a unified interface for storing and searching vector embeddings. It supports multiple backends (FAISS, Weaviate, Qdrant, Pinecone, Milvus) and enables semantic search, RAG, and similarity matching.

### What is a Vector Store?

A **vector store** is a database optimized for storing and searching high-dimensional vectors (embeddings). It enables:
- **Semantic Search**: Find documents similar to a query based on meaning
- **Similarity Matching**: Compare vectors to find similar items
- **Hybrid Search**: Combine vector search with keyword/metadata filtering
- **Scalable Storage**: Handle millions of vectors efficiently

### Why Use the Vector Store Module?

- **Multiple Backends**: Switch between FAISS (local), Weaviate, Qdrant, Pinecone, and Milvus
- **Unified Interface**: Same API regardless of backend
- **Hybrid Search**: Combine vector similarity with metadata filtering
- **Performance**: Optimized for high-throughput search operations
- **Namespace Support**: Multi-tenant isolation via namespaces
- **Metadata Filtering**: Rich filtering capabilities for precise queries

### How It Works

1. **Index Creation**: Create an index optimized for your vector dimensions
2. **Vector Storage**: Store embeddings with associated metadata
3. **Query Processing**: Convert query text to embedding and search
4. **Hybrid Search**: Combine vector similarity with metadata filters
5. **Result Ranking**: Rank results by relevance and return top-k

<div class="grid cards" markdown>

-   :material-database:{ .lg .middle } **Multi-Backend Support**

    ---
    
    Seamlessly switch between FAISS (Local), Weaviate, Qdrant, Pinecone, and Milvus

-   :material-magnify-plus:{ .lg .middle } **Hybrid Search**

    ---

    Combine dense vector similarity with sparse keyword/metadata filtering

-   :material-filter:{ .lg .middle } **Metadata Filtering**

    ---

    Rich filtering capabilities (eq, ne, gt, lt, in, contains)

-   :material-layers-triple:{ .lg .middle } **Namespace Isolation**

    ---

    Multi-tenant support via isolated namespaces

-   :material-flash:{ .lg .middle } **Performance**

    ---

    Batch operations, index optimization, and caching

-   :material-cloud-upload:{ .lg .middle } **Cloud & Local**

    ---

    Support for both embedded (local) and cloud-native deployments

</div>

!!! tip "When to Use"
    - **Semantic Search**: Finding documents similar to a query
    - **RAG**: Retrieving context for LLM generation
    - **Memory**: Storing agent memories as embeddings
    - **Recommendation**: Finding similar items based on vector proximity

---

## ⚙️ Algorithms Used

### Similarity Metrics
- **Cosine Similarity**: `A · B / ||A|| ||B||` (Default for semantic search)
- **Euclidean Distance (L2)**: `||A - B||`
- **Dot Product**: `A · B` (Faster, requires normalized vectors)

### Indexing (FAISS)
- **Flat**: Exact search (brute force). High accuracy, slow for large datasets.
- **IVF (Inverted File)**: Partitions space into Voronoi cells. Faster search.
- **HNSW**: Hierarchical Navigable Small World graphs. Best trade-off for speed/accuracy.
- **PQ (Product Quantization)**: Compresses vectors for memory efficiency.

### Hybrid Search
- **Reciprocal Rank Fusion (RRF)**: Combines ranked lists from vector search and keyword search.
  `Score = 1 / (k + rank_vector) + 1 / (k + rank_keyword)`
- **Pre-filtering**: Apply metadata filters *before* vector search (supported by most backends).

---

## Main Classes

### VectorStore

The main facade for all vector operations.

**Methods:**

| Method | Description |
|--------|-------------|
| `store_vectors(vectors, metadata)` | Store embeddings |
| `add_documents(documents, metadata, batch_size, parallel)` | **(New)** Store documents with automatic embedding generation and parallelization |
| `embed_batch(texts)` | **(New)** Generate embeddings for a batch of texts |
| `search(query, k)` | Semantic search |
| `delete(ids)` | Remove vectors |

**Example:**

```python
from veritasreason.vector_store import VectorStore

# Initialize (defaults to FAISS, parallel enabled by default with 6 workers)
store = VectorStore(backend="faiss", dimension=1536)

# 1. Store pre-computed vectors
ids = store.store_vectors(
    vectors=[[0.1, 0.2, ...], ...],
    metadata=[{"text": "Hello"}, ...]
)

# 2. Store raw documents (High Performance)
# Automatically handles embedding generation in parallel batches (uses default 6 workers)
ids = store.add_documents(
    documents=["Doc 1", "Doc 2", ...],
    metadata=[{"id": 1}, {"id": 2}, ...],
    batch_size=32,
    parallel=True
)

# Search
results = store.search(query_vector=[0.1, 0.2, ...], k=5)
```

---

### VectorIndexer

Vector indexing engine for creating and managing vector indices.

**Methods:**

| Method | Description |
|--------|-------------|
| `create_index(vectors, ids)` | Create vector index |
| `train_index(index, vectors)` | Train index on vectors |
| `add_to_index(index, vectors)` | Add vectors to index |
| `optimize_index(index)` | Optimize index performance |

**Example:**

```python
from veritasreason.vector_store import VectorIndexer
import numpy as np

indexer = VectorIndexer(backend="faiss", dimension=768)

# Create index
vectors = [np.random.rand(768) for _ in range(1000)]
vector_ids = [f"vec_{i}" for i in range(1000)]
index = indexer.create_index(vectors, vector_ids)

# Optimize index
indexer.optimize_index(index)
```

---

### VectorRetriever

Vector retrieval and similarity search engine.

**Methods:**

| Method | Description |
|--------|-------------|
| `search_similar(query, vectors, ids, k)` | Find k most similar vectors |
| `batch_search(queries, vectors, ids, k)` | Batch similarity search |
| `get_vector(vector_id)` | Retrieve vector by ID |

**Example:**

```python
from veritasreason.vector_store import VectorRetriever
import numpy as np

retriever = VectorRetriever(backend="faiss")

# Search similar vectors
query_vector = np.random.rand(768)
vectors = [np.random.rand(768) for _ in range(1000)]
vector_ids = [f"vec_{i}" for i in range(1000)]

results = retriever.search_similar(query_vector, vectors, vector_ids, k=10)
print(f"Found {len(results)} similar vectors")
```

---

### VectorManager

Vector store management and operations coordinator.

**Methods:**

| Method | Description |
|--------|-------------|
| `create_store(backend, config)` | Create vector store |
| `get_store(store_id)` | Get store by ID |
| `list_stores()` | List all stores |
| `delete_store(store_id)` | Delete store |

**Example:**

```python
from veritasreason.vector_store import VectorManager

manager = VectorManager()

# Create store
store = manager.create_store("faiss", {"dimension": 768})

# List stores
stores = manager.list_stores()
print(f"Active stores: {stores}")
```

---

### HybridSearch

Combines vector and metadata search.

**Methods:**

| Method | Description |
|--------|-------------|
| `search(query_vec, filter)` | Execute hybrid query |

**Example:**

```python
from veritasreason.vector_store import HybridSearch, MetadataFilter

searcher = HybridSearch(store)
filters = MetadataFilter().eq("category", "news").gt("date", "2023-01-01")

results = searcher.search(
    query_vector=emb,
    filter=filters,
    k=10
)
```

### Store Backends

Backend-specific implementations:
- `FAISSStore`: Local, in-memory/disk.
- `WeaviateStore`: Schema-aware vector DB.
- `QdrantStore`: Rust-based high-performance DB.
- `MilvusStore`: Scalable cloud-native DB.

#### FAISSStore

Local vector storage with multiple index types.

**Helper Classes:**
- `FAISSIndex`: Index wrapper
- `FAISSSearch`: Search operations  
- `FAISSIndexBuilder`: Index construction

**Example:**

```python
from veritasreason.vector_store import FAISSStore, FAISSIndexBuilder
import numpy as np

store = FAISSStore(dimension=768)

# Create HNSW index
builder = FAISSIndexBuilder()
index = builder.build(index_type="hnsw", dimension=768, m=16)

# Add vectors
vectors = np.random.rand(1000, 768).astype('float32')
store.add_vectors(vectors, ids=[f"vec_{i}" for i in range(1000)])

# Search
query = np.random.rand(768).astype('float32')
distances, indices = store.search(index, query, k=10)
```

#### WeaviateStore

Schema-aware vector database with GraphQL.

**Helper Classes:**
- `WeaviateClient`: Client wrapper
- `WeaviateSchema`: Schema management
- `WeaviateQuery`: GraphQL queries

**Example:**

```python
from veritasreason.vector_store import WeaviateStore

store = WeaviateStore(url="http://localhost:8080")
store.connect()

# Create schema
store.create_schema(
    "Document",
    properties=[{"name": "text", "dataType": "text"}]
)

# Add objects
store.add_objects(
    objects=[{"text": "Hello world"}],
    vectors=[[0.1, 0.2, ...]]
)
```

#### QdrantStore

High-performance Rust-based vector database.

**Helper Classes:**
- `QdrantClient`: Client wrapper
- `QdrantCollection`: Collection management
- `QdrantSearch`: Search operations

**Example:**

```python
from veritasreason.vector_store import QdrantStore

store = QdrantStore(url="http://localhost:6333")
store.connect()

# Create collection
collection = store.create_collection("my-collection", dimension=768)

# Upsert with payload
store.upsert_vectors(
    collection,
    vectors=[[0.1, 0.2, ...], ...],
    ids=["vec_1", "vec_2"],
    payloads=[{"category": "news"}, ...]
)
```

#### MilvusStore

Scalable cloud-native vector database.

**Helper Classes:**
- `MilvusClient`: Client wrapper
- `MilvusCollection`: Collection management
- `MilvusSearch`: Search operations

**Example:**

```python
from veritasreason.vector_store import MilvusStore

store = MilvusStore(host="localhost", port="19530")
store.connect()

# Create collection
collection = store.create_collection(
    "my-collection",
    dimension=768,
    metric_type="L2"
)

# Insert vectors
store.insert_vectors(collection, vectors, ids)
```

---

## Metadata and Hybrid Search

### MetadataFilter

Metadata filtering for hybrid search.

**Operators:**
- `eq(field, value)`: Equality
- `ne(field, value)`: Not equal
- `gt(field, value)`: Greater than
- `lt(field, value)`: Less than
- `in_list(field, values)`: In list
- `contains(field, value)`: Contains

**Example:**

```python
from veritasreason.vector_store import MetadataFilter

filter = MetadataFilter() \
    .eq("category", "science") \
    .gt("year", 2020) \
    .in_list("tags", ["AI", "ML"])

# Test metadata
metadata = {"category": "science", "year": 2023, "tags": ["AI"]}
matches = filter.matches(metadata)  # True
```

### SearchRanker

Result ranking and fusion for multi-source search.

**Strategies:**
- `reciprocal_rank_fusion`: RRF algorithm
- `weighted_average`: Weighted score fusion

**Example:**

```python
from veritasreason.vector_store import SearchRanker

ranker = SearchRanker(strategy="reciprocal_rank_fusion")

# Fuse multiple result lists
results1 = [{"id": "vec_1", "score": 0.9}, ...]
results2 = [{"id": "vec_2", "score": 0.85}, ...]

fused = ranker.rank([results1, results2], k=60)
```

### MetadataStore

Metadata storage and querying.

**Methods:**

| Method | Description |
|--------|-------------|
| `store_metadata(id, metadata)` | Store metadata |
| `get_metadata(id)` | Retrieve metadata |
| `query_metadata(conditions, operator)` | Query by metadata |

**Example:**

```python
from veritasreason.vector_store import MetadataStore

store = MetadataStore()
store.store_metadata("vec_1", {"category": "science", "year": 2023})

# Query
matching_ids = store.query_metadata({"category": "science"}, operator="AND")
```

### MetadataIndex

Metadata indexing for fast lookups.

**Example:**

```python
from veritasreason.vector_store import MetadataIndex

index = MetadataIndex()
index.index_metadata("vec_1", {"category": "science"})

# Query indexed metadata
matching_ids = index.query({"category": "science"}, operator="AND")
```

### MetadataSchema

Schema validation for metadata.

**Example:**

```python
from veritasreason.vector_store import MetadataSchema

schema = MetadataSchema({
    "category": {"type": str, "required": True},
    "year": {"type": int, "required": True}
})

# Validate
is_valid = schema.validate({"category": "science", "year": 2023})
```

---

## Namespace Management

### NamespaceManager

Multi-tenant namespace isolation.

**Methods:**

| Method | Description |
|--------|-------------|
| `create_namespace(name, description)` | Create namespace |
| `add_vector_to_namespace(id, namespace)` | Add vector to namespace |
| `get_namespace_vectors(namespace)` | Get namespace vectors |
| `delete_namespace(name)` | Delete namespace |

**Example:**

```python
from veritasreason.vector_store import NamespaceManager

manager = NamespaceManager()

# Create namespace
namespace = manager.create_namespace("tenant1", "Tenant 1 vectors")

# Add vectors
for i in range(100):
    manager.add_vector_to_namespace(f"vec_{i}", "tenant1")

# Get vectors
vectors = manager.get_namespace_vectors("tenant1")
```

### Namespace

Namespace dataclass with access control.

**Attributes:**
- `name`: Namespace name
- `description`: Description
- `metadata`: Additional metadata
- `permissions`: Access control permissions

**Example:**

```python
from veritasreason.vector_store import Namespace

namespace = Namespace(
    name="docs",
    description="Document vectors",
    metadata={"owner": "user1"}
)

# Set permissions
namespace.set_access_control("user1", ["read", "write"])
namespace.set_access_control("user2", ["read"])

# Check permissions
has_write = namespace.has_permission("user1", "write")  # True
```

---

## Convenience Functions

Quick access wrappers for common vector store operations.

### store_vectors

Store vectors with metadata.

```python
from veritasreason.vector_store import store_vectors

ids = store_vectors(
    vectors=[[0.1, 0.2, ...], ...],
    metadata=[{"text": "Hello"}, ...],
    method="default"
)
```

### search_vectors

Search for similar vectors.

```python
from veritasreason.vector_store import search_vectors

results = search_vectors(
    query_vector=[0.1, 0.2, ...],
    vectors=all_vectors,
    vector_ids=all_ids,
    k=10,
    method="default"
)
```

### update_vectors

Update existing vectors.

```python
from veritasreason.vector_store import update_vectors

success = update_vectors(
    vector_ids=["vec_1", "vec_2"],
    new_vectors=[[0.2, 0.3, ...], ...],
    method="default"
)
```

### delete_vectors

Delete vectors by ID.

```python
from veritasreason.vector_store import delete_vectors

success = delete_vectors(
    vector_ids=["vec_1", "vec_2"],
    method="default"
)
```

### create_index

Create vector index.

```python
from veritasreason.vector_store import create_index

index = create_index(
    vectors=[[0.1, 0.2, ...], ...],
    index_type="hnsw",
    method="default"
)
```

### hybrid_search

Hybrid vector and metadata search.

```python
from veritasreason.vector_store import hybrid_search, MetadataFilter

filter = MetadataFilter().eq("category", "news")
results = hybrid_search(
    query_vector=[0.1, 0.2, ...],
    vectors=all_vectors,
    metadata=all_metadata,
    vector_ids=all_ids,
    filter=filter,
    k=10,
    method="default"
)
```

### filter_metadata

Filter vectors by metadata.

```python
from veritasreason.vector_store import filter_metadata

matching_ids = filter_metadata(
    metadata=all_metadata,
    conditions={"category": "news"},
    operator="AND",
    method="default"
)
```

### manage_namespace

Manage vector namespaces.

```python
from veritasreason.vector_store import manage_namespace

namespace = manage_namespace(
    action="create",
    namespace="tenant1",
    description="Tenant 1 vectors",
    method="default"
)
```

### get_vector_store_method

Get registered vector store method.

```python
from veritasreason.vector_store import get_vector_store_method

method = get_vector_store_method(task="store", name="custom_store")
```

### list_available_methods

List all registered methods.

```python
from veritasreason.vector_store import list_available_methods

methods = list_available_methods()
print(f"Available methods: {methods}")
```

---

## Configuration

### Environment Variables

```bash
export VECTOR_STORE_BACKEND=weaviate
export WEAVIATE_URL=http://localhost:8080
```

### YAML Configuration

```yaml
vector_store:
  backend: faiss # or weaviate, qdrant, milvus
  dimension: 1536
  metric: cosine
  
  faiss:
    index_type: HNSW
    
  weaviate:
    url: http://localhost:8080
```

---

## Integration Examples

### RAG Retrieval

```python
from veritasreason.embeddings import EmbeddingGenerator
from veritasreason.vector_store import VectorStore

# 1. Embed Query
embedder = EmbeddingGenerator()
query_vec = embedder.generate("What is the capital of France?")

# 2. Search
store = VectorStore()
results = store.search(query_vec, k=3)

# 3. Use Context
context = "\n".join([r.metadata['text'] for r in results])
print(f"Context: {context}")
```

---

## Best Practices

1.  **Normalize Vectors**: Always normalize vectors if using Cosine Similarity or Dot Product.
2.  **Use HNSW**: For FAISS, `HNSW` is usually the best default index type for performance/recall balance.
3.  **Batch Operations**: Use `store_vectors` with batches (e.g., 100 items) rather than one by one.
4.  **Filter First**: In hybrid search, restrictive filters significantly improve performance.

---

## Troubleshooting

**Issue**: `DimensionMismatchError`
**Solution**: Ensure your embedding model dimension (e.g., 1536 for OpenAI) matches the VectorStore dimension.

**Issue**: FAISS index not saved.
**Solution**: Call `store.save("index.faiss")` explicitly for local FAISS indices, or use a persistent backend like Weaviate/Qdrant.

---

## See Also
- [High-Performance Usage Guide](../vector_store_usage.md) - **(New)** Parallel ingestion and batching guide
- [Embeddings Module](embeddings.md) - Generates the vectors
- [Context Module](context.md) - Uses vector store for memory
- [Ingest Module](ingest.md) - Source of data

## Cookbook

Interactive tutorials to learn vector stores:

- **[Vector Store](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/introduction/13_Vector_Store.ipynb)**: Set up and use vector stores for similarity search
  - **Topics**: FAISS, Weaviate, Qdrant, hybrid search, metadata filtering
  - **Difficulty**: Intermediate
  - **Use Cases**: Storing and searching embeddings, building RAG systems

- **[Advanced Vector Store and Search](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/advanced/Advanced_Vector_Store_and_Search.ipynb)**: Advanced vector store operations and optimization
  - **Topics**: Index optimization, hybrid search, performance tuning, namespace management
  - **Difficulty**: Advanced
  - **Use Cases**: Production deployments, performance optimization

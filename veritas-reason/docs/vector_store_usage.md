# High-Performance Vector Store Usage

This guide demonstrates how to leverage the new high-performance features of the VeritasReason Vector Store, specifically designed for efficient batch processing and parallel ingestion of large document sets.

## 🚀 Key Features

- **Parallel Ingestion**: Utilize multi-threading to embed and store documents concurrently.
- **Batch Processing**: Automatically group documents into batches to minimize overhead.
- **Unified API**: A single `add_documents` method handles embedding generation and storage.

---

## ⚡ Quick Start: Parallel Ingestion

The fastest way to ingest documents is using the `add_documents` method. Parallelization is enabled by default with optimized settings (6 workers).

```python
from veritasreason.vector_store import VectorStore
import time

store = VectorStore(
    backend="faiss",
    dimension=768,
)

documents = [f"This is document number {i} with some content." for i in range(1000)]
metadata = [{"source": "generated", "id": i} for i in range(1000)]

start_time = time.time()
ids = store.add_documents(
    documents=documents,
    metadata=metadata,
    batch_size=64,
    parallel=True,
)
print(f"Ingested {len(ids)} documents in {time.time() - start_time:.2f}s")
```

---

## 📊 Performance Comparison

### Old Method (Sequential Loop)
*Slower due to sequential processing and overhead per single item.*

```python
for doc in documents:
    emb = embedder.generate(doc)
    store.store_vectors([emb], [{"text": doc}])
```

### New Method (Parallel Batching)
*Significantly faster (3x-10x) by utilizing thread pools and batch operations.*

```python
store.add_documents(documents, parallel=True)
```

---

## 🛠 Configuration & Tuning

### `max_workers`
Controls the number of concurrent threads used for embedding generation.
- **Default**: 6 (Optimized for most systems)
- **Recommendation**: You generally don't need to change this. If you have very high core counts or specific throughput needs, you can override it.

```python
store = VectorStore(max_workers=16)
```

### `batch_size`
Controls how many documents are processed in a single chunk.
- **Default**: 32
- **Recommendation**: 
    - **Local Models**: 32-64 usually works well.
    - **API Models (OpenAI, etc.)**: Larger batches (e.g., 100-200) can reduce network latency overhead.

```python
store.add_documents(documents, batch_size=100)
```

---

## 🧩 Advanced: Manual Batch Embedding

If you need the embeddings without storing them immediately, use `embed_batch`.

```python
vectors = store.embed_batch(
    texts=documents[:100],
)

print(f"Generated {len(vectors)} vectors")
```

## ⚠️ Best Practices

1.  **Metadata Consistency**: Ensure your `metadata` list has the same length as your `documents` list.
2.  **Error Handling**: The `add_documents` method will propagate exceptions if embedding fails. Ensure your data is clean.
3.  **Memory Usage**: Very large `batch_size` combined with high `max_workers` can increase memory usage. Monitor your system resources.

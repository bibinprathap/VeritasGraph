# Embeddings Module Usage Guide

This guide demonstrates how to use the embeddings module for generating and managing embeddings for text content.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Text Embedding](#text-embedding)
3. [Checking Embedding Methods](#checking-embedding-methods)
4. [Pooling Strategies](#pooling-strategies)
5. [Similarity Calculation](#similarity-calculation)
6. [Provider Stores](#provider-stores)
7. [Vector Embedding Manager](#vector-embedding-manager)
8. [Graph Embedding Manager](#graph-embedding-manager)
9. [Using Methods](#using-methods)
10. [Using Registry](#using-registry)
11. [Configuration](#configuration)
12. [Advanced Examples](#advanced-examples)

## Basic Usage

### Using Main Classes

```python
from veritasreason.embeddings import EmbeddingGenerator

# Create embedding generator
generator = EmbeddingGenerator()

# Generate embeddings
embeddings = generator.generate_embeddings(
    "Hello world",
    data_type="text"
)

print(f"Embedding shape: {embeddings.shape}")
print(f"Embedding dimension: {len(embeddings)}")
```

## Text Embedding

### FastEmbed Embedding (Default)

VeritasReason uses FastEmbed by default for efficient, local embedding generation.

```python
from veritasreason.embeddings import TextEmbedder

# Create text embedder (uses FastEmbed by default)
embedder = TextEmbedder()

# Single text embedding
embedding = embedder.embed_text("The quick brown fox jumps over the lazy dog")
print(f"Embedding shape: {embedding.shape}")

# Batch text embedding (FastEmbed is optimized for batch processing)
texts = [
    "Python is a programming language",
    "Machine learning is fascinating",
    "Natural language processing"
]
embeddings = embedder.embed_batch(texts)
print(f"Batch embeddings shape: {embeddings.shape}")  # (3, embedding_dim)
```

### Sentence-Transformers Embedding

You can also use sentence-transformers models if preferred.

```python
from veritasreason.embeddings import TextEmbedder

# Create text embedder with specific model
embedder = TextEmbedder(
    method="sentence_transformers",
    model_name="all-MiniLM-L6-v2",
    device="cpu",
    normalize=True
)

# Single text embedding
embedding = embedder.embed_text("The quick brown fox jumps over the lazy dog")
print(f"Embedding shape: {embedding.shape}")
print(f"Embedding dimension: {embedder.get_embedding_dimension()}")
```

### Using Text Embedding Methods

```python
from veritasreason.embeddings.methods import embed_text

# Using FastEmbed (Default, fast and efficient)
emb = embed_text("Hello world", method="fastembed")

# Using sentence-transformers (Legacy/Alternative)
emb = embed_text("Hello world", method="sentence_transformers")

# Using fallback (hash-based)
emb = embed_text("Hello world", method="fallback")

# Batch processing
texts = ["text1", "text2", "text3"]
embs_fast = embed_text(texts, method="fastembed")  # Faster batch processing
embs = embed_text(texts, method="sentence_transformers")
```

## Checking Embedding Methods

### Dynamic Model Switching

You can switch the embedding model and provider dynamically without creating a new instance.

```python
from veritasreason.embeddings import TextEmbedder, EmbeddingGenerator

# 1. Switch model in TextEmbedder
embedder = TextEmbedder(method="sentence_transformers")
print(f"Current method: {embedder.get_method()}")

# Switch to FastEmbed
try:
    embedder.set_model(method="fastembed", model_name="BAAI/bge-small-en-v1.5")
    print(f"Switched to: {embedder.get_method()}")
except ImportError:
    print("FastEmbed not installed")

# 2. Switch model in EmbeddingGenerator
generator = EmbeddingGenerator()
generator.set_text_model(method="sentence_transformers", model_name="all-MiniLM-L6-v2")
```

### Checking Active Method in TextEmbedder

```python
from veritasreason.embeddings import TextEmbedder

# Create embedder with specific method
embedder = TextEmbedder(method="fastembed", model_name="BAAI/bge-small-en-v1.5")

# Check which method is currently active
method = embedder.get_method()
print(f"Active method: {method}")  # "fastembed", "sentence_transformers", or "fallback"

# Get comprehensive model information
info = embedder.get_model_info()
print(f"Method: {info['method']}")
print(f"Model: {info['model_name']}")
print(f"Model loaded: {info['model_loaded']}")
print(f"Dimension: {info['dimension']}")
print(f"Normalize: {info['normalize']}")
if 'device' in info:
    print(f"Device: {info['device']}")
```

### Checking Methods in EmbeddingGenerator

```python
from veritasreason.embeddings import EmbeddingGenerator

# Create generator
generator = EmbeddingGenerator()

# Check text embedding method
text_method = generator.get_text_method()
print(f"Text method: {text_method}")

# Get all methods information at once
methods_info = generator.get_methods_info()
print(f"Text embedder: {methods_info['text']}")
```

### Checking Available Providers

```python
from veritasreason.embeddings import check_available_providers

# Check which embedding providers are installed and available
providers = check_available_providers()

print("Available providers:")
for provider, available in providers.items():
    status = "✓ Available" if available else "✗ Not available"
    print(f"  {provider}: {status}")

# Use providers conditionally
if providers["fastembed"]:
    embedder = TextEmbedder(method="fastembed")
    print("Using FastEmbed for embeddings")
elif providers["sentence_transformers"]:
    embedder = TextEmbedder(method="sentence_transformers")
    print("Using Sentence Transformers for embeddings")
else:
    embedder = TextEmbedder()
    print("Using fallback method for embeddings")
```

### Listing All Available Methods

```python
from veritasreason.embeddings import list_available_methods

# List all available methods
all_methods = list_available_methods()
print("All available methods:")
for task, methods in all_methods.items():
    print(f"  {task}: {methods}")

# List methods for specific task
text_methods = list_available_methods("text")
print(f"Text embedding methods: {text_methods['text']}")
```

## Pooling Strategies

### Mean Pooling

```python
from veritasreason.embeddings import MeanPooling

pooling = MeanPooling()
embeddings = ...  # (n_embeddings, dim)
pooled = pooling.pool(embeddings)
print(f"Pooled shape: {pooled.shape}")  # (dim,)
```

### Max Pooling

```python
from veritasreason.embeddings import MaxPooling

pooling = MaxPooling()
pooled = pooling.pool(embeddings)
```

### CLS Token Pooling

```python
from veritasreason.embeddings import CLSPooling

pooling = CLSPooling()
pooled = pooling.pool(embeddings)  # Returns first embedding
```

### Attention-Based Pooling

```python
from veritasreason.embeddings import AttentionPooling

pooling = AttentionPooling()
pooled = pooling.pool(embeddings)  # Softmax-weighted sum
```

### Hierarchical Pooling

```python
from veritasreason.embeddings import HierarchicalPooling

pooling = HierarchicalPooling()
pooled = pooling.pool(embeddings, chunk_size=10)
```

### Using Pooling Methods

```python
from veritasreason.embeddings.methods import pool_embeddings

# Mean pooling
pooled = pool_embeddings(embeddings, method="mean")

# Max pooling
pooled = pool_embeddings(embeddings, method="max")

# Attention pooling
pooled = pool_embeddings(embeddings, method="attention")

# Hierarchical pooling
pooled = pool_embeddings(embeddings, method="hierarchical", chunk_size=10)
```

## Similarity Calculation

### Cosine Similarity

```python
from veritasreason.embeddings import EmbeddingGenerator

generator = EmbeddingGenerator()

emb1 = generator.generate_embeddings("Hello world", data_type="text")
emb2 = generator.generate_embeddings("Hi there", data_type="text")

similarity = generator.compare_embeddings(emb1, emb2, method="cosine")
print(f"Cosine similarity: {similarity:.3f}")
```

### Euclidean Similarity

```python
from veritasreason.embeddings import EmbeddingGenerator

generator = EmbeddingGenerator()

similarity = generator.compare_embeddings(emb1, emb2, method="euclidean")
print(f"Euclidean similarity: {similarity:.3f}")
```

### Using Similarity Methods

```python
from veritasreason.embeddings.methods import calculate_similarity

# Cosine similarity
sim = calculate_similarity(emb1, emb2, method="cosine")

# Euclidean similarity
sim = calculate_similarity(emb1, emb2, method="euclidean")
```

## Provider Stores

### OpenAI Embeddings

```python
from veritasreason.embeddings import OpenAIStore

# Create OpenAI store
store = OpenAIStore(
    api_key="your-api-key",
    model="text-embedding-3-small"
)

# Generate embedding
embedding = store.embed("Hello world")
print(f"OpenAI embedding shape: {embedding.shape}")
```

### BGE Embeddings

```python
from veritasreason.embeddings import BGEStore

# Create BGE store
store = BGEStore(
    model_name="BAAI/bge-small-en-v1.5"
)

# Generate embedding
embedding = store.embed("Hello world")
```

### FastEmbed Embeddings

```python
from veritasreason.embeddings import FastEmbedStore

# Create FastEmbed store
store = FastEmbedStore(
    model_name="BAAI/bge-small-en-v1.5"
)

# Single embedding
embedding = store.embed("Hello world")
print(f"FastEmbed embedding shape: {embedding.shape}")

# Batch embeddings (FastEmbed is optimized for batch processing)
texts = ["text1", "text2", "text3"]
embeddings = store.embed_batch(texts)
print(f"Batch embeddings shape: {embeddings.shape}")
```

### Provider Factory

```python
from veritasreason.embeddings import ProviderStoreFactory

# Create provider using factory
store = ProviderStoreFactory.create(
    "openai",
    api_key="your-api-key"
)

embedding = store.embed("Hello world")

# Create FastEmbed store using factory
fastembed_store = ProviderStoreFactory.create(
    "fastembed",
    model_name="BAAI/bge-small-en-v1.5"
)
embedding = fastembed_store.embed("Hello world")
```

## Vector Embedding Manager

### Preparing Embeddings for Vector Databases

```python
from veritasreason.embeddings import VectorEmbeddingManager
import numpy as np

# Create vector embedding manager
manager = VectorEmbeddingManager()

# Generate embeddings (example)
embeddings = np.random.rand(10, 384).astype(np.float32)
metadata = [{"text": f"document_{i}", "category": "science"} for i in range(10)]

# Prepare for FAISS
formatted = manager.prepare_for_vector_db(
    embeddings,
    metadata=metadata,
    backend="faiss"
)

print(f"Vectors shape: {formatted['vectors'].shape}")
print(f"Number of vectors: {len(formatted['ids'])}")
print(f"Backend: {formatted['backend']}")
```

### Preparing for Different Vector DB Backends

```python
from veritasreason.embeddings import VectorEmbeddingManager

manager = VectorEmbeddingManager()

# Prepare for Weaviate
weaviate_data = manager.prepare_for_vector_db(
    embeddings,
    metadata=metadata,
    backend="weaviate",
    class_name="Document"
)

# Prepare for Qdrant
qdrant_data = manager.prepare_for_vector_db(
    embeddings,
    metadata=metadata,
    backend="qdrant"
)

# Prepare for Milvus
milvus_data = manager.prepare_for_vector_db(
    embeddings,
    metadata=metadata,
    backend="milvus"
)
```

### Validating Embedding Dimensions

```python
from veritasreason.embeddings import VectorEmbeddingManager

manager = VectorEmbeddingManager()

# Validate dimensions for specific backend
is_valid = manager.validate_dimensions(embeddings, backend="weaviate")
if is_valid:
    print("Embeddings meet Weaviate requirements")
else:
    print("Embeddings do not meet requirements")
```

### Normalizing Embeddings

```python
from veritasreason.embeddings import VectorEmbeddingManager

manager = VectorEmbeddingManager()

# Normalize embeddings for vector DB storage
normalized = manager.normalize_for_storage(embeddings, method="l2")
print(f"Normalized embeddings shape: {normalized.shape}")
```

### Batch Preparation

```python
from veritasreason.embeddings import VectorEmbeddingManager

manager = VectorEmbeddingManager()

# Prepare multiple batches
embeddings_batch1 = np.random.rand(5, 384).astype(np.float32)
embeddings_batch2 = np.random.rand(5, 384).astype(np.float32)

batch_result = manager.batch_prepare(
    [embeddings_batch1, embeddings_batch2],
    backend="faiss"
)

print(f"Combined vectors shape: {batch_result['vectors'].shape}")
print(f"Number of batches: {batch_result['num_batches']}")
```

## Graph Embedding Manager

### Preparing Embeddings for Graph Databases

```python
from veritasreason.embeddings import GraphEmbeddingManager

# Create graph embedding manager
manager = GraphEmbeddingManager()

# Define entities (nodes)
entities = [
    {"id": "e1", "text": "John Doe", "type": "Person"},
    {"id": "e2", "text": "Acme Corporation", "type": "Organization"},
    {"id": "e3", "text": "Software Engineer", "type": "Role"}
]

# Define relationships (edges)
relationships = [
    {"source": "e1", "target": "e2", "type": "WORKS_FOR", "text": "works at"},
    {"source": "e1", "target": "e3", "type": "HAS_ROLE", "text": "has role"}
]

# Prepare for Neo4j
result = manager.prepare_for_graph_db(
    entities,
    relationships,
    backend="neo4j"
)

print(f"Node embeddings: {len(result['node_embeddings'])} nodes")
print(f"Edge embeddings: {len(result['edge_embeddings'])} edges")
print(f"Backend: {result['backend']}")
```

### Creating Node Embeddings

```python
from veritasreason.embeddings import GraphEmbeddingManager

manager = GraphEmbeddingManager()

# Create embeddings for graph nodes
entities = [
    {"id": "n1", "text": "Entity 1", "type": "Person"},
    {"id": "n2", "text": "Entity 2", "type": "Organization"}
]

node_embeddings = manager.create_node_embeddings(entities, backend="neo4j")

for node_id, embedding in node_embeddings.items():
    print(f"Node {node_id}: embedding shape {embedding.shape}")
```

### Creating Edge Embeddings

```python
from veritasreason.embeddings import GraphEmbeddingManager

manager = GraphEmbeddingManager()

# Create embeddings for graph edges
relationships = [
    {"source": "n1", "target": "n2", "type": "RELATES_TO", "text": "related to"}
]

edge_embeddings = manager.create_edge_embeddings(relationships, backend="neo4j")

for edge_id, embedding in edge_embeddings.items():
    print(f"Edge {edge_id}: embedding shape {embedding.shape}")
```

### Embedding Entities and Relationships

```python
from veritasreason.embeddings import GraphEmbeddingManager

manager = GraphEmbeddingManager()

# Embed entities
entities = [
    {"id": "e1", "text": "Entity 1"},
    {"id": "e2", "text": "Entity 2"}
]
entity_embeddings = manager.embed_entities(entities)

# Embed relationships
relationships = [
    {"source": "e1", "target": "e2", "type": "CONNECTED_TO"}
]
relationship_embeddings = manager.embed_relationships(relationships)
```

### Integration with Different Graph DB Backends

```python
from veritasreason.embeddings import GraphEmbeddingManager

manager = GraphEmbeddingManager()

entities = [
    {"id": "n1", "text": "Node 1"},
    {"id": "n2", "text": "Node 2"}
]

# Prepare for Neo4j
neo4j_result = manager.prepare_for_graph_db(
    entities,
    backend="neo4j",
    database="my_database",
    label="Node"
)

# Prepare for NetworkX
networkx_result = manager.prepare_for_graph_db(
    entities,
    backend="networkx",
    graph_type="DiGraph"
)

# Prepare for FalkorDB
falkordb_result = manager.prepare_for_graph_db(
    entities,
    backend="falkordb",
    graph_name="my_graph"
)
```

## Using Methods

### Generate Embeddings

```python
from veritasreason.embeddings.methods import generate_embeddings

# Auto-detect data type
emb = generate_embeddings("Hello world", method="default")

# Explicit text embedding
emb = generate_embeddings("Hello world", method="text")

# Image embedding
emb = generate_embeddings("image.jpg", method="image")

# Audio embedding
emb = generate_embeddings("audio.wav", method="audio")
```

### Batch Processing

```python
from veritasreason.embeddings.methods import embed_text, embed_image

# Batch text embeddings
texts = ["text1", "text2", "text3"]
embeddings = embed_text(texts, method="sentence_transformers")

# Batch image embeddings
images = ["img1.jpg", "img2.png"]
embeddings = embed_image(images, method="clip")
```

## Using Registry

### Registering Custom Methods

```python
from veritasreason.embeddings.registry import method_registry

def custom_text_embedding(text: str, **kwargs):
    """Custom text embedding function."""
    # Your custom implementation
    return embedding_vector

# Register custom method
method_registry.register("text", "custom_method", custom_text_embedding)

# Use custom method
from veritasreason.embeddings.methods import embed_text
emb = embed_text("Hello world", method="custom_method")
```

### Listing Available Methods

```python
from veritasreason.embeddings.methods import list_available_methods

# List all methods
all_methods = list_available_methods()
print(all_methods)

# List methods for specific task
text_methods = list_available_methods("text")
print(text_methods)
```

### Getting Registered Methods

```python
from veritasreason.embeddings.methods import get_embedding_method

# Get method from registry
method = get_embedding_method("text", "custom_method")
if method:
    result = method("Hello world")
```

## Configuration

### Environment Variables

```bash
# Set embedding configuration via environment variables
export EMBEDDING_MODEL="all-MiniLM-L6-v2"
export EMBEDDING_BATCH_SIZE=32
export EMBEDDING_DIMENSION=384
export EMBEDDING_NORMALIZE="true"
export EMBEDDING_DEVICE="cpu"
export EMBEDDING_COMPRESSION_METHOD="pca"
export EMBEDDING_WINDOW_SIZE=512
export EMBEDDING_OVERLAP=50
```

### Programmatic Configuration

```python
from veritasreason.embeddings.config import embeddings_config

# Set configuration
embeddings_config.set("model", "sentence-transformers/all-mpnet-base-v2")
embeddings_config.set("batch_size", 64)
embeddings_config.set("normalize", True)

# Get configuration
model = embeddings_config.get("model", default="all-MiniLM-L6-v2")
batch_size = embeddings_config.get("batch_size", default=32)

# Method-specific configuration
embeddings_config.set_method_config("text", model_name="all-MiniLM-L6-v2")
text_config = embeddings_config.get_method_config("text")
```

### Config File (YAML)

```yaml
embeddings:
  model: "all-MiniLM-L6-v2"
  batch_size: 32
  dimension: 384
  normalize: true
  device: "cpu"
  window_size: 512
  overlap: 50

embeddings_methods:
  text:
    model_name: "all-MiniLM-L6-v2"
    device: "cpu"
    normalize: true
  image:
    model_name: "ViT-B/32"
    device: "cpu"
    normalize: true
```

```python
from veritasreason.embeddings.config import EmbeddingsConfig

# Load from config file
config = EmbeddingsConfig(config_file="config.yaml")
```

## Advanced Examples

### Complete Embedding Pipeline

```python
from veritasreason.embeddings import (
    EmbeddingGenerator,
    calculate_similarity
)

# Step 1: Generate embeddings
generator = EmbeddingGenerator()
texts = ["text1", "text2", "text3"]
embeddings = generator.generate_embeddings(texts, data_type="text")

# Step 2: Calculate similarities
similarity = calculate_similarity(embeddings[0], embeddings[1], method="cosine")
print(f"Similarity: {similarity:.3f}")
```

### Text-Image Search

```python
from veritasreason.embeddings import EmbeddingGenerator, calculate_similarity

generator = EmbeddingGenerator()

# Embed query (text)
query_emb = generator.generate_embeddings("A cat sitting on a mat", data_type="text")

# Embed documents (images)
doc_embs = [
    generator.generate_embeddings("cat1.jpg", data_type="image"),
    generator.generate_embeddings("dog1.jpg", data_type="image"),
    generator.generate_embeddings("cat2.jpg", data_type="image"),
]

# Find most similar
similarities = [
    calculate_similarity(query_emb, doc_emb, method="cosine")
    for doc_emb in doc_embs
]

most_similar_idx = max(range(len(similarities)), key=lambda i: similarities[i])
print(f"Most similar image: doc_{most_similar_idx}")
```

### Batch Processing with Context Windows

```python
from veritasreason.embeddings import ContextManager, TextEmbedder

# Create context manager
context_manager = ContextManager(window_size=512, overlap=50)

# Create text embedder
embedder = TextEmbedder()

# Process long document
long_document = "..."  # Your long document
windows = context_manager.split_into_windows(long_document)

# Generate embeddings for each window
window_embeddings = []
for window in windows:
    emb = embedder.embed_text(window.text)
    window_embeddings.append(emb)

# Pool window embeddings
from veritasreason.embeddings.methods import pool_embeddings
document_embedding = pool_embeddings(
    np.array(window_embeddings),
    method="mean"
)
```

### Custom Embedding Method

```python
from veritasreason.embeddings.registry import method_registry
from veritasreason.embeddings.methods import embed_text
import numpy as np

def tfidf_embedding(text: str, **kwargs):
    """Custom TF-IDF based embedding."""
    # Your TF-IDF implementation
    # This is a placeholder
    return np.random.rand(128).astype(np.float32)

# Register custom method
method_registry.register("text", "tfidf", tfidf_embedding)

# Use custom method
embedding = embed_text("Hello world", method="tfidf")
```

## Best Practices

1. **Normalize Embeddings**: Always normalize embeddings for consistent similarity calculations
   ```python
   embedder = TextEmbedder(normalize=True)
   ```

2. **Batch Processing**: Use batch processing for multiple items to improve efficiency
   ```python
   embeddings = embedder.embed_batch(texts)  # Faster than loop
   ```

3. **Context Windows**: Use context windows for long texts to maintain semantic coherence
   ```python
   windows = manager.split_into_windows(long_text, preserve_sentences=True)
   ```

4. **Configuration Management**: Use environment variables or config files for consistent settings
   ```python
   embeddings_config.set("model", "all-MiniLM-L6-v2")
   ```

5. **Error Handling**: Always handle fallback methods when dependencies are unavailable
   ```python
   try:
       emb = embed_text(text, method="sentence_transformers")
   except:
       emb = embed_text(text, method="fallback")
   ```

## Performance Tips

1. **GPU Acceleration**: Use GPU for faster processing when available
   ```python
   embedder = TextEmbedder(device="cuda")
   ```

2. **Batch Size**: Adjust batch size based on available memory
   ```python
   embeddings_config.set("batch_size", 64)  # Larger for more memory
   ```

3. **Caching**: Cache embeddings for repeated queries
   ```python
   # Store embeddings in cache/database for reuse
   ```

4. **Parallel Processing**: Process multiple files in parallel when possible
   ```python
   from concurrent.futures import ThreadPoolExecutor
   with ThreadPoolExecutor() as executor:
       embeddings = list(executor.map(embed_image, image_paths))
   ```


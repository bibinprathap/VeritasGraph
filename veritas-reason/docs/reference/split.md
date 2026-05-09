# Split

> **Comprehensive document chunking and splitting for optimal processing with 15+ methods including KG-aware, semantic, and structural chunking.**

---

## 🎯 Overview

<div class="grid cards" markdown>

-   :material-content-cut:{ .lg .middle } **Multiple Methods**

    ---

    15+ chunking methods: recursive, semantic, entity-aware, relation-aware, and more

-   :material-graph:{ .lg .middle } **KG-Aware Chunking**

    ---

    Preserve entities, relationships, and graph structure for GraphRAG workflows

-   :material-brain:{ .lg .middle } **Semantic Chunking**

    ---

    Intelligent boundary detection using embeddings and NLP

-   :material-file-tree:{ .lg .middle } **Structural Chunking**

    ---

    Respect document structure: headings, paragraphs, lists, tables

-   :material-check-circle:{ .lg .middle } **Quality Validation**

    ---

    Chunk quality assessment and validation

-   :material-source-branch:{ .lg .middle } **Provenance Tracking**

    ---

    Track chunk origins for data lineage

</div>

!!! tip "Choosing the Right Method"
    - **Standard Documents**: Use `recursive` or `sentence` for general text
    - **GraphRAG**: Use `entity_aware` or `relation_aware` to preserve knowledge
    - **Semantic Coherence**: Use `semantic_transformer` for topic-based chunks
    - **Structured Docs**: Use `structural` for documents with headings/sections
    - **Large Documents**: Use `hierarchical` for multi-level chunking

---

## ⚙️ Algorithms Used

### Standard Splitting Algorithms

**Purpose**: Split documents into chunks using various strategies.

**How it works**:

- **Recursive Splitting**: Separator hierarchy (`` `\n\n` ``, `` `\n` ``, `` ` ` ``, ``) with greedy splitting
- **Token Counting**: BPE tokenization using tiktoken or transformers
- **Sentence Segmentation**: NLTK punkt, spaCy sentencizer, or regex-based
- **Paragraph Detection**: Double newline detection with whitespace normalization
- **Character Splitting**: Fixed-size character chunks with overlap
- **Word Splitting**: Whitespace tokenization with word boundary preservation

### Semantic Chunking Algorithms

**Purpose**: Intelligent boundary detection using embeddings and NLP.

**How it works**:

- **Semantic Boundary Detection**:
  - Sentence transformer embeddings (384-1024 dim)
  - Cosine similarity between consecutive sentences
  - Threshold-based boundary detection (default: `` `0.7` ``)
- **LLM-based Splitting**:
  - Prompt engineering for optimal split point detection
  - Context window management
  - Coherence scoring

### KG/Ontology Chunking Algorithms

**Purpose**: Preserve entities, relationships, and graph structure for GraphRAG workflows.

**How it works**:

- **Entity Boundary Detection**:
  - NER-based entity extraction (spaCy, LLM)
  - Entity span tracking
  - Boundary preservation (no entity splitting)
- **Triplet Preservation**:
  - Graph-based triplet integrity checking
  - Subject-predicate-object span tracking
  - Relationship boundary preservation
- **Graph Centrality Analysis**:
  - Degree centrality: `` `C_D(v) = deg(v) / (n-1)` ``
  - Betweenness centrality: `` `C_B(v) = Σ(σ_st(v) / σ_st)` ``
  - Closeness centrality: `` `C_C(v) = (n-1) / Σd(v,u)` ``
  - Eigenvector centrality: Power iteration method
- **Community Detection**:
  - Louvain algorithm: Modularity optimization O(n log n)
  - Leiden algorithm: Improved Louvain with refinement
  - Modularity calculation: `Q = (1/2m) Σ[A_ij - k_i*k_j/2m]δ(c_i,c_j)`

### Structural Chunking Algorithms
- **Heading Detection**: Markdown/HTML heading parsing
- **List Detection**: Ordered/unordered list identification
- **Table Detection**: Table boundary identification
- **Section Hierarchy**: Tree-based section structure

### Validation Algorithms
- **Chunk Size Validation**: Min/max size checking
- **Overlap Validation**: Overlap percentage calculation
- **Completeness Check**: Coverage verification
- **Quality Scoring**: Multi-factor quality assessment

---

## Main Classes

### TextSplitter

Unified text splitter with method parameter for all chunking strategies.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `split(text)` | Split text using configured method | Method-specific algorithm |
| `split_documents(documents)` | Batch split documents | Parallel processing |
| `split_with_metadata(text, metadata)` | Split with metadata preservation | Metadata propagation |
| `validate_chunks(chunks)` | Validate chunk quality | Quality assessment |

**Supported Methods:**

| Category | Methods |
|----------|---------|
| **Standard** | recursive, token, sentence, paragraph, character, word |
| **Semantic** | semantic_transformer, llm, huggingface, nltk |
| **KG/Ontology** | entity_aware, relation_aware, graph_based, ontology_aware |
| **Advanced** | hierarchical, community_detection, centrality_based, subgraph, topic_based |

**Configuration Options:**

```python
TextSplitter(
    method="recursive",           # Chunking method
    chunk_size=1000,             # Target chunk size (characters/tokens)
    chunk_overlap=200,           # Overlap between chunks
    length_function=len,         # Function to measure chunk size
    separators=["\n\n", "\n", " ", ""],  # For recursive method
    keep_separator=True,         # Keep separators in chunks
    add_start_index=True,        # Add start index to metadata
    strip_whitespace=True,       # Strip whitespace from chunks
    
    # Semantic chunking options
    embedding_model="all-MiniLM-L6-v2",  # For semantic_transformer
    similarity_threshold=0.7,    # Semantic boundary threshold
    
    # Entity-aware options
    ner_method="ml",             # NER method (ml/spacy, llm, pattern)
    preserve_entities=True,      # Don't split entities
    
    # LLM options
    llm_provider="openai",       # LLM provider
    llm_model="gpt-4",          # LLM model
    
    # Graph-based options
    centrality_method="degree",  # Centrality measure
    community_algorithm="louvain",  # Community detection algorithm
)
```

**Example:**

```python
from veritasreason.split import TextSplitter

# Standard recursive splitting
splitter = TextSplitter(
    method="recursive",
    chunk_size=1000,
    chunk_overlap=200
)
chunks = splitter.split(long_text)

for i, chunk in enumerate(chunks):
    print(f"Chunk {i}: {len(chunk.text)} chars")
    print(f"Metadata: {chunk.metadata}")

# Entity-aware for GraphRAG
splitter = TextSplitter(
    method="entity_aware",
    ner_method="ml",
    chunk_size=1000,
    preserve_entities=True
)
chunks = splitter.split(text)

# Semantic chunking
splitter = TextSplitter(
    method="semantic_transformer",
    embedding_model="all-MiniLM-L6-v2",
    similarity_threshold=0.7
)
chunks = splitter.split(text)

# Hierarchical chunking
splitter = TextSplitter(
    method="hierarchical",
    chunk_sizes=[2000, 1000, 500],  # Multi-level
    chunk_overlaps=[400, 200, 100]
)
chunks = splitter.split(text)
```

---

### SemanticChunker

Semantic-based chunking using embeddings and similarity.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `chunk(text)` | Chunk by semantic boundaries | Embedding similarity |
| `find_boundaries(sentences)` | Find semantic boundaries | Threshold-based detection |
| `calculate_similarity(sent1, sent2)` | Calculate similarity | Cosine similarity |

**Example:**

```python
from veritasreason.split import SemanticChunker

chunker = SemanticChunker(
    embedding_model="all-MiniLM-L6-v2",
    similarity_threshold=0.7,
    min_chunk_size=100,
    max_chunk_size=2000
)

chunks = chunker.chunk(long_text)

for chunk in chunks:
    print(f"Chunk: {chunk.text[:100]}...")
    print(f"Coherence score: {chunk.metadata.get('coherence_score')}")
```

---

### EntityAwareChunker

Preserve entity boundaries during chunking for GraphRAG.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `chunk(text, entities)` | Chunk preserving entities | Entity boundary detection |

**Example:**

```python
from veritasreason.split import EntityAwareChunker
from veritasreason.semantic_extract import NERExtractor

# Extract entities first
ner = NERExtractor(method="ml")
entities = ner.extract(text)

# Chunk preserving entities
chunker = EntityAwareChunker(
    chunk_size=1000,
    chunk_overlap=200,
    ner_method="ml"
)

chunks = chunker.chunk(text, entities=entities)

for chunk in chunks:
    print(f"Entities in chunk: {chunk.metadata.get('entities')}")
```

---

### RelationAwareChunker

Preserve relationship triplets during chunking.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `chunk(text, relationships)` | Chunk preserving triplets | Triplet span tracking |
| `extract_relationships(text)` | Extract relationships | Relation extraction |
| `validate_triplet_integrity(chunk, relationships)` | Validate triplets | Integrity checking |

**Example:**

```python
from veritasreason.split import RelationAwareChunker
from veritasreason.semantic_extract import RelationExtractor

# Extract relationships
rel_extractor = RelationExtractor()
relationships = rel_extractor.extract(text)

# Chunk preserving relationships
chunker = RelationAwareChunker(
    chunk_size=1000,
    preserve_triplets=True
)

chunks = chunker.chunk(text, relationships=relationships)

for chunk in chunks:
    print(f"Relationships: {chunk.metadata.get('relationships')}")
```

---

### GraphBasedChunker

Chunk based on graph structure and centrality.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `chunk(text, graph)` | Chunk by graph structure | Centrality-based |
| `calculate_centrality(graph)` | Calculate node centrality | Degree/betweenness/closeness |
| `detect_communities(graph)` | Detect communities | Louvain/Leiden algorithm |

**Example:**

```python
from veritasreason.split import GraphBasedChunker
from veritasreason.kg import GraphBuilder

# Build graph
builder = GraphBuilder()
kg = builder.build(entities, relationships)

# Chunk by graph structure
chunker = GraphBasedChunker(
    centrality_method="betweenness",
    community_algorithm="louvain"
)

chunks = chunker.chunk(text, graph=kg)

for chunk in chunks:
    print(f"Community: {chunk.metadata.get('community_id')}")
    print(f"Centrality: {chunk.metadata.get('avg_centrality')}")
```

---

### StructuralChunker

Structure-aware chunking respecting document hierarchy.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `chunk(text)` | Chunk by structure | Heading/section detection |
| `_extract_structure(text)` | Extract structural elements | Markdown/HTML parsing |

**Example:**

```python
from veritasreason.split import StructuralChunker

chunker = StructuralChunker(
    respect_headers=True,
    respect_sections=True,
    max_chunk_size=2000
)

chunks = chunker.chunk(markdown_text)

for chunk in chunks:
    print(f"Structure preserved: {chunk.metadata.get('structure_preserved')}")
    print(f"Elements: {chunk.metadata.get('element_types')}")
```

---

### HierarchicalChunker

Multi-level hierarchical chunking.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `chunk(text)` | Multi-level chunking | Recursive hierarchical split |

**Example:**

```python
from veritasreason.split import HierarchicalChunker

chunker = HierarchicalChunker(
    chunk_sizes=[2000, 1000, 500],
    chunk_overlaps=[400, 200, 100],
    create_parent_chunks=True
)

chunks = chunker.chunk(long_text)

for chunk in chunks:
    print(f"Level: {chunk.metadata.get('level')}")
    print(f"Parent: {chunk.metadata.get('parent_id')}")
    print(f"Children: {chunk.metadata.get('child_ids')}")
```

---

### OntologyAwareChunker

Chunk based on ontology concepts and relationships.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `chunk(text, ontology)` | Chunk by ontology concepts | Concept boundary detection |
| `extract_concepts(text)` | Extract ontology concepts | Concept extraction |
| `find_concept_boundaries(text, concepts)` | Find concept boundaries | Concept span checking |

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chunk_size` | int | 1000 | Target chunk size |
| `chunk_overlap` | int | 200 | Overlap between chunks |
| `ontology_path` | str | None | Path to ontology file (.owl, .rdf) |
| `preserve_concepts` | bool | True | Don't split ontology concepts |
| `concept_extraction_method` | str | "llm" | Method for concept extraction |

**Example:**

```python
from veritasreason.split import OntologyAwareChunker

chunker = OntologyAwareChunker(
    chunk_size=1000,
    chunk_overlap=200,
    ontology_path="domain_ontology.owl",
    preserve_concepts=True,
    concept_extraction_method="llm"
)

chunks = chunker.chunk(text)

for chunk in chunks:
    concepts = chunk.metadata.get('concepts', [])
    print(f"Concepts in chunk: {[c['label'] for c in concepts]}")
    print(f"Concept types: {[c['type'] for c in concepts]}")
```

---

### SlidingWindowChunker

Fixed-size sliding window chunking with configurable step size.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `chunk(text)` | Sliding window chunking | Fixed-size window with step |
| `chunk_with_overlap(text)` | Chunk with specific overlap | Window position calculation |

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chunk_size` | int | 1000 | Size of sliding window |
| `overlap` | int | 0 | Overlap size |
| `stride` | int | chunk_size - overlap | Step size |

**Example:**

```python
from veritasreason.split import SlidingWindowChunker

# Basic sliding window
chunker = SlidingWindowChunker(
    chunk_size=1000,
    overlap=200
)

chunks = chunker.chunk(long_text)

for i, chunk in enumerate(chunks):
    print(f"Window {i}: chars {chunk.start_index}-{chunk.end_index}")
    print(f"Has overlap: {chunk.metadata.get('has_overlap')}")

# Boundary-preserving sliding window
chunks = chunker.chunk(text, preserve_boundaries=True)
```

---

### TableChunker

Table-specific chunking preserving table structure.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `chunk_table(table_data)` | Chunk tables | Row/Column-based splitting |
| `chunk_to_text_chunks(table_data)` | Convert table chunks to text | Table to text conversion |
| `extract_table_schema(table_data)` | Extract schema | Type inference and schema extraction |

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_rows` | int | 100 | Maximum rows per table chunk |
| `preserve_headers` | bool | True | Keep headers in each chunk |
| `chunk_by_columns` | bool | False | Chunk by columns instead of rows |

**Example:**

```python
from veritasreason.split import TableChunker

chunker = TableChunker(
    max_rows=50,
    preserve_headers=True,
    chunk_by_columns=False
)

table_data = {
    "headers": ["Col1", "Col2", "Col3"],
    "rows": [["Val1", "Val2", "Val3"], ...]
}

# Get structured table chunks
table_chunks = chunker.chunk_table(table_data)

# Get text chunks for RAG
text_chunks = chunker.chunk_to_text_chunks(table_data)

for chunk in text_chunks:
    print(f"Table chunk {chunk.metadata.get('chunk_index')}")
    print(f"Rows: {chunk.metadata.get('row_count')}")
```

---

### ChunkValidator

Validate chunk quality and completeness.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `validate(chunks)` | Validate chunks | Multi-factor validation |
| `check_size(chunk)` | Check size constraints | Min/max checking |
| `check_overlap(chunks)` | Check overlap | Overlap calculation |
| `check_completeness(chunks, original)` | Check coverage | Coverage verification |
| `calculate_quality_score(chunk)` | Quality score | Multi-factor scoring |

**Example:**

```python
from veritasreason.split import ChunkValidator

validator = ChunkValidator(
    min_chunk_size=100,
    max_chunk_size=2000,
    min_overlap=50,
    max_overlap=500
)

validation_result = validator.validate(chunks)

print(f"Valid: {validation_result['valid']}")
print(f"Issues: {validation_result['issues']}")
print(f"Quality score: {validation_result['quality_score']}")
```

---

### ProvenanceTracker

Track chunk provenance for data lineage.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `track(chunk, source)` | Track chunk origin | Provenance recording |
| `get_lineage(chunk_id)` | Get chunk lineage | Lineage retrieval |
| `visualize_lineage(chunk_id)` | Visualize lineage | Graph visualization |

**Example:**

```python
from veritasreason.split import ProvenanceTracker

tracker = ProvenanceTracker()

for chunk in chunks:
    tracker.track(
        chunk=chunk,
        source={
            "document_id": "doc123",
            "file_path": "data/document.pdf",
            "page": 5,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )

# Get lineage
lineage = tracker.get_lineage(chunk.id)
print(f"Source: {lineage['source']}")
print(f"Transformations: {lineage['transformations']}")
```

---

## Convenience Functions

Quick access to splitting operations:

```python
from veritasreason.split import (
    split_recursive,
    split_by_tokens,
    split_by_sentences,
    split_by_paragraphs,
    split_entity_aware,
    split_relation_aware,
    split_semantic_transformer,
    list_available_methods
)

# List available methods
methods = list_available_methods()
print(f"Available methods: {methods}")

# Quick splitting
chunks = split_recursive(text, chunk_size=1000, chunk_overlap=200)
chunks = split_by_sentences(text, sentences_per_chunk=5)
chunks = split_entity_aware(text, ner_method="ml")
```

---

## Configuration

### Environment Variables

```bash
# Default settings
export SPLIT_DEFAULT_METHOD=recursive
export SPLIT_DEFAULT_CHUNK_SIZE=1000
export SPLIT_DEFAULT_CHUNK_OVERLAP=200

# Semantic chunking
export SPLIT_EMBEDDING_MODEL=all-MiniLM-L6-v2
export SPLIT_SIMILARITY_THRESHOLD=0.7

# Entity-aware
export SPLIT_NER_METHOD=ml  # or spacy
export SPLIT_PRESERVE_ENTITIES=true

# LLM-based
export SPLIT_LLM_PROVIDER=openai
export SPLIT_LLM_MODEL=gpt-4
```

### YAML Configuration

```yaml
# config.yaml - Split Module Configuration

split:
  default_method: recursive
  chunk_size: 1000
  chunk_overlap: 200
  
  recursive:
    separators: ["\n\n", "\n", " ", ""]
    keep_separator: true
    
  semantic:
    embedding_model: all-MiniLM-L6-v2
    similarity_threshold: 0.7
    min_chunk_size: 100
    max_chunk_size: 2000
    
  entity_aware:
    ner_method: ml  # or spacy
    preserve_entities: true
    min_entity_gap: 50
    
  relation_aware:
    preserve_triplets: true
    relation_extraction_method: llm
    
  graph_based:
    centrality_method: betweenness
    community_algorithm: louvain
    min_community_size: 3
    
  hierarchical:
    levels: 3
    chunk_sizes: [2000, 1000, 500]
    chunk_overlaps: [400, 200, 100]
    
  validation:
    enabled: true
    min_chunk_size: 100
    max_chunk_size: 2000
    check_overlap: true
    check_completeness: true
```

---

## Method Comparison

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **recursive** | General text | Fast, simple | May split mid-sentence |
| **sentence** | Coherent chunks | Respects sentences | Variable size |
| **semantic_transformer** | Topic coherence | Semantic boundaries | Slower, needs embeddings |
| **entity_aware** | GraphRAG | Preserves entities | Requires NER |
| **relation_aware** | KG extraction | Preserves triplets | Requires relation extraction |
| **graph_based** | Graph analysis | Graph-aware | Requires graph construction |
| **hierarchical** | Large documents | Multi-level | More complex |
| **structural** | Formatted docs | Respects structure | Needs structure |

---

## Integration Examples

### Complete GraphRAG Pipeline

```python
from veritasreason.split import TextSplitter
from veritasreason.semantic_extract import NERExtractor, RelationExtractor
from veritasreason.kg import GraphBuilder
from veritasreason.embeddings import EmbeddingGenerator
from veritasreason.vector_store import VectorStore

# Parse document
text = "Apple Inc. was founded by Steve Jobs in 1976..."

# Entity-aware chunking
splitter = TextSplitter(
    method="entity_aware",
    ner_method="llm",
    chunk_size=1000
)
chunks = splitter.split(text)

# Extract from each chunk
ner = NERExtractor(method="llm")
rel_extractor = RelationExtractor()

all_entities = []
all_relationships = []

for chunk in chunks:
    entities = ner.extract(chunk.text)
    relationships = rel_extractor.extract(chunk.text, entities)
    
    all_entities.extend(entities)
    all_relationships.extend(relationships)

# Build knowledge graph
builder = GraphBuilder()
kg = builder.build(all_entities, all_relationships)

# Generate embeddings
embedder = EmbeddingGenerator()
embeddings = embedder.generate([chunk.text for chunk in chunks])

# Store in vector store
vector_store = VectorStore()
vector_store.store(embeddings, chunks)
```

### Multi-Level Hierarchical Chunking

```python
from veritasreason.split import HierarchicalChunker

chunker = HierarchicalChunker(
    chunk_sizes=[4000, 2000, 1000],
    chunk_overlaps=[800, 400, 200],
    create_parent_chunks=True
)

chunks = chunker.chunk(very_long_document)

# Access hierarchy
for chunk in chunks:
    level = chunk.metadata['level']
    parent_id = chunk.metadata.get('parent_id')
    child_ids = chunk.metadata.get('child_ids', [])
    
    print(f"Level {level}: {len(chunk.text)} chars")
    if parent_id:
        print(f"  Parent: {parent_id}")
    if child_ids:
        print(f"  Children: {len(child_ids)}")
```

---

## Best Practices

### 1. Choose Appropriate Chunk Size

```python
# For semantic search (embeddings)
splitter = TextSplitter(method="recursive", chunk_size=512)

# For LLM context (GPT-4)
splitter = TextSplitter(method="recursive", chunk_size=4000)

# For entity extraction
splitter = TextSplitter(method="entity_aware", chunk_size=1000)
```

### 2. Use Overlap for Context

```python
# 20% overlap recommended
splitter = TextSplitter(
    chunk_size=1000,
    chunk_overlap=200  # 20%
)
```

### 3. Validate Chunks

```python
from veritasreason.split import ChunkValidator

validator = ChunkValidator()
validation = validator.validate(chunks)

if not validation['valid']:
    print(f"Issues: {validation['issues']}")
```

### 4. Track Provenance

```python
from veritasreason.split import ProvenanceTracker

tracker = ProvenanceTracker()
for chunk in chunks:
    tracker.track(chunk, source={"doc_id": "123"})
```

---

## Troubleshooting

### Issue: Chunks too small/large

```python
# Solution: Adjust chunk size and method
splitter = TextSplitter(
    method="recursive",
    chunk_size=1500,  # Increase
    chunk_overlap=300
)

# Or use validation
validator = ChunkValidator(min_chunk_size=500, max_chunk_size=2000)
```

### Issue: Entities split across chunks

```python
# Solution: Use entity-aware chunking
splitter = TextSplitter(
    method="entity_aware",
    ner_method="llm",
    preserve_entities=True
)
```

### Issue: Slow semantic chunking

```python
# Solution: Use faster embedding model or batch processing
splitter = TextSplitter(
    method="semantic_transformer",
    embedding_model="all-MiniLM-L6-v2",  # Faster model
    batch_size=32  # Batch embeddings
)
```

---

## Performance Tips

### Memory Optimization

```python
# Process in batches
def chunk_large_corpus(documents, batch_size=100):
    splitter = TextSplitter(method="recursive")
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        chunks = splitter.split_documents(batch)
        yield from chunks
```

### Speed Optimization

```python
# Use faster methods for large documents
splitter = TextSplitter(
    method="recursive",  # Fastest
    chunk_size=1000
)

# Avoid LLM-based for large corpora
# Use semantic_transformer instead of llm
```

---

## See Also
- [Parse Module](parse.md) - Document parsing
- [Semantic Extract Module](semantic_extract.md) - Entity extraction
- [Knowledge Graph Module](kg.md) - Graph construction
- [Embeddings Module](embeddings.md) - Vector generation
- [Vector Store Module](vector_store.md) - Vector storage

## Cookbook

Interactive tutorials to learn text chunking and splitting:

- **[Chunking and Splitting](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/introduction/11_Chunking_and_Splitting.ipynb)**: Split documents for RAG and processing
  - **Topics**: Recursive character splitting, semantic splitting, token-based splitting, chunking strategies
  - **Difficulty**: Beginner
  - **Use Cases**: Preparing text for RAG, document chunking

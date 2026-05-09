# Knowledge Graph

> **High-level KG construction, management, and analysis system.**

---

## 🎯 Overview

The **Knowledge Graph (KG) Module** is the core module for building, managing, and analyzing knowledge graphs. It transforms extracted entities and relationships into structured, queryable knowledge graphs.

### What is a Knowledge Graph?

A **knowledge graph** is a structured representation of information where:
- **Nodes** represent entities (people, organizations, concepts, etc.)
- **Edges** represent relationships between entities
- **Properties** store additional information about nodes and edges

Knowledge graphs enable semantic queries, relationship traversal, and complex reasoning that traditional databases cannot handle.

### Why Use the KG Module?

- **Structured Knowledge**: Transform unstructured data into structured, queryable graphs
- **Entity Resolution**: Automatically merge duplicate entities using fuzzy matching
- **Temporal Support**: Track how knowledge changes over time
- **Graph Analytics**: Analyze graph structure, importance, and communities
- **Provenance Tracking**: Know where every piece of information came from

### How It Works

1. **Input**: Entities and relationships from semantic extraction
2. **Entity Resolution**: Merge similar entities to avoid duplicates
3. **Graph Construction**: Build nodes and edges from entities and relationships
4. **Enrichment**: Add temporal information, provenance, and metadata
5. **Analysis**: Perform graph analytics (centrality, communities, etc.)

<div class="grid cards" markdown>

-   :material-graph-outline:{ .lg .middle } **KG Construction**

    ---

    Build graphs from entities and relationships with automatic merging

-   :material-clock-time-four-outline:{ .lg .middle } **Temporal Graphs**

    ---

    Time-aware edges (`valid_from`, `valid_until`) and temporal queries

-   :material-account-multiple-check:{ .lg .middle } **Entity Resolution**

    ---

    Resolve entities using fuzzy matching and semantic similarity

-   :material-chart-network:{ .lg .middle } **Graph Analytics**

    ---

    Centrality, Community Detection, and Connectivity analysis

-   :material-history:{ .lg .middle } **Provenance**

    ---

    Track the source and lineage of every node and edge

</div>

!!! tip "When to Use"
    - **KG Building**: The primary module for assembling a KG from extracted data
    - **Entity Resolution**: Resolving and merging similar entities
    - **Analysis**: Understanding the structure and importance of nodes
    - **Time-Series**: Modeling how the graph evolves over time

!!! note "Related Modules"
    - **Conflict Detection**: Use `veritasreason.conflicts` module for conflict detection and resolution
    - **Deduplication**: Use `veritasreason.deduplication` module for advanced deduplication

---

## ⚙️ Algorithms & Components

### 🏗️ Graph Construction

#### GraphBuilder
Constructs knowledge graphs from raw entities and relationships.

**Key Features:**
- Entity and relationship creation
- Automatic entity resolution and merging
- Provenance tracking for all operations
- Temporal graph support
- Multi-source data integration

**Methods:**
| Method | Description |
|--------|-------------|
| `build(sources)` | Build graph from multiple data sources |
| `build_single_source(data)` | Build graph from single data source |
| `merge_entities()` | Merge duplicate entities during building |

**Example:**
```python
from veritasreason.kg import GraphBuilder

builder = GraphBuilder(merge_entities=True)
kg = builder.build([source1, source2])
```

### 🔍 Node Embeddings

#### NodeEmbedder
Generates node embeddings for structural similarity analysis.

**Supported Algorithms:**
- **Node2Vec**: Biased random walk based embeddings (high quality)
- **DeepWalk**: Unbiased random walk based embeddings (simpler, faster)
- **Word2Vec**: Neural network training on graph walks

**Key Features:**
- Configurable embedding dimensions and walk parameters
- Biased and unbiased random walk generation
- Embedding storage as node properties
- Similarity search based on learned embeddings

**Methods:**
| Method | Description |
|--------|-------------|
| `compute_embeddings()` | Main interface for embedding computation |
| `find_similar_nodes()` | Find structurally similar nodes |
| `store_embeddings()` | Store embeddings as node properties |

**Example:**
```python
from veritasreason.kg import NodeEmbedder

embedder = NodeEmbedder(method="node2vec", embedding_dimension=128)
embeddings = embedder.compute_embeddings(graph_store, ["Entity"], ["RELATED_TO"])
similar_nodes = embedder.find_similar_nodes(graph_store, "entity_123", top_k=10)
```

### 📏 Similarity Analysis

#### SimilarityCalculator
Computes similarity between node embeddings and vectors.

**Supported Algorithms:**
- **Cosine Similarity**: Measures angular similarity between vectors
- **Euclidean Distance**: Calculates straight-line distance
- **Manhattan Distance**: Computes L1 distance (sum of absolute differences)
- **Pearson Correlation**: Measures linear correlation
- **Batch Similarity**: Efficient computation for multiple embeddings
- **Pairwise Similarity**: All-vs-all similarity matrix

**Key Features:**
- Individual and batch similarity calculations
- Multiple similarity metrics
- Performance optimization with sparse matrices
- Top-k most similar node finding

**Methods:**
| Method | Description |
|--------|-------------|
| `cosine_similarity()` | Calculate cosine similarity |
| `euclidean_distance()` | Calculate Euclidean distance |
| `manhattan_distance()` | Calculate Manhattan distance |
| `correlation_similarity()` | Calculate Pearson correlation |
| `batch_similarity()` | Batch similarity computation |
| `find_most_similar()` | Find top-k similar nodes |

**Example:**
```python
from veritasreason.kg import SimilarityCalculator

calc = SimilarityCalculator()
similarity = calc.cosine_similarity(embedding1, embedding2)
similarities = calc.batch_similarity(embeddings, query_embedding)
most_similar = calc.find_most_similar(embeddings, query_embedding, top_k=5)
```

### 🛤️ Path Finding

#### PathFinder
Discovers paths and routes in knowledge graphs.

**Supported Algorithms:**
- **Dijkstra's Algorithm**: Weighted shortest path finding
- **A* Search**: Heuristic-based path finding
- **BFS Shortest Path**: Unweighted shortest path finding
- **All Shortest Paths**: Multiple path discovery
- **K-Shortest Paths**: Top-k alternative paths

**Key Features:**
- Weighted and unweighted graph support
- Custom heuristic functions for A*
- Multiple path discovery and ranking
- Efficient path reconstruction

**Methods:**
| Method | Description |
|--------|-------------|
| `dijkstra_shortest_path()` | Find weighted shortest path |
| `a_star_search()` | Find path using heuristics |
| `bfs_shortest_path()` | Find unweighted shortest path |
| `all_shortest_paths()` | Find all shortest paths |
| `find_k_shortest_paths()` | Find top-k alternative paths |
| `path_length()` | Calculate total path distance |

**Example:**
```python
from veritasreason.kg import PathFinder

finder = PathFinder()
path = finder.dijkstra_shortest_path(graph, "node_a", "node_b")
paths = finder.all_shortest_paths(graph, "source_node", "target_node")
k_paths = finder.find_k_shortest_paths(graph, "source", "target", k=3)
```

### 🔗 Link Prediction

#### LinkPredictor
Predicts potential connections and missing relationships.

**Supported Algorithms:**
- **Preferential Attachment**: Degree product scoring
- **Common Neighbors**: Count of shared neighbors
- **Jaccard Coefficient**: Jaccard similarity of neighbor sets
- **Adamic-Adar Index**: Weighted neighbor count based on degree
- **Resource Allocation**: Resource transfer probability

**Key Features:**
- Multiple link prediction algorithms
- Batch processing for multiple predictions
- Top-k link prediction for targeted analysis
- Scalable implementations for large graphs

**Methods:**
| Method | Description |
|--------|-------------|
| `predict_links()` | Predict potential links |
| `score_link()` | Calculate link prediction score |
| `predict_top_links()` | Find top-k links for specific node |
| `batch_score_links()` | Batch scoring for multiple pairs |

**Example:**
```python
from veritasreason.kg import LinkPredictor

predictor = LinkPredictor(method="preferential_attachment")
links = predictor.predict_links(graph, top_k=20)
score = predictor.score_link(graph, "node_a", "node_b")
```

### 🎯 Centrality Analysis

#### CentralityCalculator
Identifies important and influential nodes in graphs.

**Supported Algorithms:**
- **Degree Centrality**: Measures node connectivity
- **Betweenness Centrality**: Measures importance as bridge
- **Closeness Centrality**: Measures average distance to all nodes
- **Eigenvector Centrality**: Measures influence based on connections
- **PageRank**: Importance based on link structure

**Key Features:**
- Multiple centrality algorithms
- Centrality ranking and statistics
- Configurable parameters for iterative algorithms
- Batch calculation of all measures

**Methods:**
| Method | Description |
|--------|-------------|
| `calculate_degree_centrality()` | Calculate degree-based importance |
| `calculate_betweenness_centrality()` | Calculate bridge-based importance |
| `calculate_closeness_centrality()` | Calculate distance-based importance |
| `calculate_eigenvector_centrality()` | Calculate influence-based importance |
| `calculate_pagerank()` | Calculate PageRank scores |
| `calculate_all_centrality()` | Calculate all centrality measures |

**Example:**
```python
from veritasreason.kg import CentralityCalculator

calculator = CentralityCalculator()
centrality = calculator.calculate_degree_centrality(graph)
pagerank_scores = calculator.calculate_pagerank(graph, damping_factor=0.85)
top_nodes = calculator.get_top_nodes(centrality, top_k=10)
```

### 👥 Community Detection

#### CommunityDetector
Identifies clusters and communities in graphs.

**Supported Algorithms:**
- **Louvain**: Modularity optimization with hierarchical clustering
- **Leiden**: Improved version of Louvain with guaranteed connectivity
- **Label Propagation**: Fast, semi-supervised detection
- **K-Clique Communities**: Overlapping community detection

**Key Features:**
- Multiple community detection algorithms
- Community quality metrics (modularity, size distribution)
- Overlapping and non-overlapping communities
- Configurable resolution parameters

**Methods:**
| Method | Description |
|--------|-------------|
| `detect_communities()` | Main interface for community detection |
| `detect_communities_louvain()` | Louvain modularity optimization |
| `detect_communities_leiden()` | Leiden algorithm with refinement |
| `detect_communities_label_propagation()` | Fast label propagation |
| `calculate_community_metrics()` | Community quality assessment |

**Example:**
```python
from veritasreason.kg import CommunityDetector

detector = CommunityDetector()
communities = detector.detect_communities(graph, algorithm="louvain")
metrics = detector.calculate_community_metrics(graph, communities)
leiden_communities = detector.detect_communities_leiden(graph, resolution=1.2)
```

### 🔌 Connectivity Analysis

#### ConnectivityAnalyzer
Analyzes graph connectivity and structural properties.

**Supported Algorithms:**
- **Connectivity Analysis**: Determine if graph is connected
- **Connected Components**: Find all connected components using DFS
- **Shortest Paths**: BFS-based shortest path finding
- **Bridge Identification**: Find critical edges
- **Graph Density**: Measure connectivity and sparsity
- **Degree Statistics**: Analyze node degree distributions

**Key Features:**
- Comprehensive connectivity analysis
- Bridge edge identification for network robustness
- Graph structure classification
- NetworkX integration with fallback implementations

**Methods:**
| Method | Description |
|--------|-------------|
| `analyze_connectivity()` | Main connectivity analysis |
| `find_connected_components()` | Detect connected components |
| `calculate_shortest_paths()` | Find shortest paths |
| `identify_bridges()` | Find critical bridge edges |
| `calculate_graph_density()` | Compute density metrics |

**Example:**
```python
from veritasreason.kg import ConnectivityAnalyzer

analyzer = ConnectivityAnalyzer()
connectivity = analyzer.analyze_connectivity(graph)
components = analyzer.find_connected_components(graph)
bridges = analyzer.identify_bridges(graph)
```

### 📝 Provenance Tracking

#### GraphBuilderWithProvenance & AlgorithmTrackerWithProvenance
Tracks the origin and execution history of all KG operations.

**Key Features:**
- Complete provenance tracking for graph construction
- Algorithm execution tracking with parameters
- Execution IDs for workflow linking
- Metadata and timestamp tracking
- Error handling and graceful degradation

**Methods:**
| Method | Description |
|--------|-------------|
| `track_embedding_computation()` | Track embedding algorithm executions |
| `track_similarity_calculation()` | Track similarity analysis |
| `track_link_prediction()` | Track link prediction executions |
| `track_centrality_calculation()` | Track centrality calculations |
| `track_community_detection()` | Track community detection |

**Example:**
```python
from veritasreason.kg import GraphBuilderWithProvenance, AlgorithmTrackerWithProvenance

# Graph building with provenance
builder = GraphBuilderWithProvenance(provenance=True)
result = builder.build_single_source(graph_data)

# Algorithm tracking with provenance
tracker = AlgorithmTrackerWithProvenance(provenance=True)
embed_id = tracker.track_embedding_computation(
    graph=networkx_graph,
    algorithm='node2vec',
    embeddings=computed_embeddings,
    parameters={'embedding_dimension': 128}
)
```

---

## 📊 Algorithm Categories Summary

| Category | Algorithms | Use Cases |
|----------|------------|-----------|
| **Node Embeddings** | Node2Vec, DeepWalk, Word2Vec | Structural similarity, node representation |
| **Similarity Analysis** | Cosine, Euclidean, Manhattan, Correlation | Node similarity, recommendation systems |
| **Path Finding** | Dijkstra, A*, BFS, K-Shortest | Route planning, network analysis |
| **Link Prediction** | Preferential Attachment, Jaccard, Adamic-Adar | Network completion, recommendation |
| **Centrality Analysis** | Degree, Betweenness, Closeness, PageRank | Influence analysis, importance ranking |
| **Community Detection** | Louvain, Leiden, Label Propagation | Social analysis, clustering |
| **Connectivity** | Components, Bridges, Density | Network robustness, structure analysis |

---

## Using Classes

```python
from veritasreason.kg import GraphBuilder, GraphAnalyzer

# Build using GraphBuilder
builder = GraphBuilder(merge_entities=True)
kg = builder.build(sources)

# Analyze
analyzer = GraphAnalyzer()
stats = analyzer.analyze_graph(kg)
print(f"Communities: {stats.get('communities', [])}")
```

---

## Configuration

### Environment Variables

```bash
export KG_MERGE_STRATEGY=fuzzy
export KG_TEMPORAL_GRANULARITY=day
export KG_RESOLUTION_STRATEGY=fuzzy
```

### YAML Configuration

```yaml
kg:
  resolution:
    threshold: 0.9
    strategy: semantic
    
  temporal:
    enabled: true
    default_validity: infinite
```

---

## Integration Examples

### Temporal Analysis Pipeline

```python
from veritasreason.kg import GraphBuilder, TemporalGraphQuery

# 1. Build Temporal Graph
builder = GraphBuilder(enable_temporal=True)
kg = builder.build(temporal_data)

# 2. Query Evolution
query = TemporalGraphQuery(kg)
snapshot_2020 = query.at_time("2020-01-01")
snapshot_2023 = query.at_time("2023-01-01")

# 3. Compare
diff = snapshot_2023.minus(snapshot_2020)
print(f"New nodes since 2020: {len(diff.nodes)}")
```

---

## Best Practices

1.  **Clean Data First**: Use `EntityResolver` to resolve similar entities and prevent "entity explosion" (too many duplicate nodes).
2.  **Use Provenance**: Always track sources (`track_history=True`) to debug where bad data came from.
3.  **Temporal Granularity**: Choose the right granularity (Day vs Second) to balance performance and precision.
4.  **Deduplication**: Use `veritasreason.deduplication` module for advanced deduplication needs.
5.  **Conflict Resolution**: Use `veritasreason.conflicts` module for conflict detection and resolution.

---

## See Also

- [Graph Store Module](graph_store.md) - Persistence layer
- [Semantic Extract Module](semantic_extract.md) - Data source
- [Visualization Module](visualization.md) - Visualizing the KG
- [Conflicts Module](conflicts.md) - Conflict detection and resolution

## Cookbook

Interactive tutorials to learn knowledge graph construction and analysis:

- **[Building Knowledge Graphs](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/introduction/07_Building_Knowledge_Graphs.ipynb)**: Learn the fundamentals of building knowledge graphs
  - **Topics**: Graph construction, entity resolution, relationship mapping
  - **Difficulty**: Beginner
  - **Use Cases**: Understanding graph construction basics

- **[Your First Knowledge Graph](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/introduction/08_Your_First_Knowledge_Graph.ipynb)**: Build your first knowledge graph from scratch
  - **Topics**: Entity extraction, relationship extraction, graph construction, visualization
  - **Difficulty**: Beginner
  - **Use Cases**: First-time users, quick start

- **[Graph Analytics](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/introduction/10_Graph_Analytics.ipynb)**: Analyze knowledge graphs with centrality and community detection
  - **Topics**: Centrality measures, community detection, graph metrics
  - **Difficulty**: Intermediate
  - **Use Cases**: Understanding graph structure, finding important nodes

- **[Advanced Graph Analytics](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/advanced/02_Advanced_Graph_Analytics.ipynb)**: Advanced graph analysis techniques
  - **Topics**: PageRank, Louvain algorithm, shortest path, graph mining
  - **Difficulty**: Advanced
  - **Use Cases**: Complex graph analysis, research applications

- **[Temporal Knowledge Graphs](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/advanced/10_Temporal_Knowledge_Graphs.ipynb)**: Model and query data that changes over time
  - **Topics**: Time series, temporal logic, temporal queries, graph evolution
  - **Difficulty**: Advanced
  - **Use Cases**: Tracking changes over time, temporal reasoning

- **[Deduplication Module](deduplication.md)**: Advanced deduplication techniques for entity resolution

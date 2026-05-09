# Visualization Module Usage Guide

This comprehensive guide demonstrates how to use the visualization module for visualizing knowledge graphs, ontologies, embeddings, semantic networks, analytics results, and temporal graphs with interactive and static output formats.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Knowledge Graph Visualization](#knowledge-graph-visualization)
3. [Ontology Visualization](#ontology-visualization)
4. [Embedding Visualization](#embedding-visualization)
5. [Semantic Network Visualization](#semantic-network-visualization)
6. [Analytics Visualization](#analytics-visualization)
7. [Temporal Visualization](#temporal-visualization)
8. [Layout Algorithms](#layout-algorithms)
9. [Color Schemes](#color-schemes)
10. [Export Formats](#export-formats)
11. [Algorithms and Methods](#algorithms-and-methods)
12. [Configuration](#configuration)
13. [Advanced Examples](#advanced-examples)
14. [Best Practices](#best-practices)

## Basic Usage

### Using Convenience Functions

```python
from veritasreason.visualization import visualize_kg, visualize_embeddings, visualize_ontology
import numpy as np

# Knowledge graph visualization
graph = {
    "entities": [
        {"id": "e1", "label": "Entity 1", "type": "Person"},
        {"id": "e2", "label": "Entity 2", "type": "Organization"}
    ],
    "relationships": [
        {"source": "e1", "target": "e2", "label": "works_for"}
    ]
}
fig = visualize_kg(graph, output="interactive", method="default")

# Embedding visualization
embeddings = np.random.rand(100, 768)
labels = [f"label_{i}" for i in range(100)]
fig = visualize_embeddings(embeddings, labels, method="2d_projection", output="interactive")

# Ontology visualization
ontology = {
    "classes": [
        {"name": "Person", "parent": None},
        {"name": "Employee", "parent": "Person"}
    ]
}
fig = visualize_ontology(ontology, output="interactive", method="hierarchy")
```

### Using Visualizer Classes

```python
from veritasreason.visualization import (
    KGVisualizer,
    EmbeddingVisualizer,
    OntologyVisualizer
)

# Knowledge graph visualizer
kg_viz = KGVisualizer(layout="force", color_scheme="vibrant")
fig = kg_viz.visualize_network(graph, output="interactive")

# Embedding visualizer
emb_viz = EmbeddingVisualizer(color_scheme="default")
fig = emb_viz.visualize_2d_projection(embeddings, labels, method="umap")

# Ontology visualizer
ont_viz = OntologyVisualizer()
fig = ont_viz.visualize_hierarchy(ontology, output="interactive")
```

## Knowledge Graph Visualization

### Network Visualization

```python
from veritasreason.visualization import KGVisualizer

viz = KGVisualizer(layout="force", color_scheme="vibrant", node_size=15)

# Basic network visualization
graph = {
    "entities": [
        {"id": "e1", "label": "Alice", "type": "Person"},
        {"id": "e2", "label": "Bob", "type": "Person"},
        {"id": "e3", "label": "Company", "type": "Organization"}
    ],
    "relationships": [
        {"source": "e1", "target": "e2", "label": "knows"},
        {"source": "e1", "target": "e3", "label": "works_for"}
    ]
}

# Interactive visualization
fig = viz.visualize_network(graph, output="interactive")

# Save to file
viz.visualize_network(graph, output="html", file_path="network.html")
viz.visualize_network(graph, output="png", file_path="network.png", width=1200, height=800)
```

### Community Visualization

```python
from veritasreason.visualization import KGVisualizer

viz = KGVisualizer(layout="force", color_scheme="vibrant")

communities = {
    "node_assignments": {
        "e1": 0,
        "e2": 0,
        "e3": 1
    },
    "num_communities": 2
}

fig = viz.visualize_communities(graph, communities, output="interactive", file_path="communities.html")
```

### Centrality Visualization

```python
from veritasreason.visualization import KGVisualizer

viz = KGVisualizer(layout="force")

centrality = {
    "e1": 0.8,
    "e2": 0.5,
    "e3": 0.3
}

fig = viz.visualize_centrality(
    graph, 
    centrality, 
    centrality_type="degree",
    output="interactive",
    file_path="centrality.html"
)
```

### Entity Type Distribution

```python
from veritasreason.visualization import KGVisualizer

viz = KGVisualizer()

fig = viz.visualize_entity_types(graph, output="interactive", file_path="entity_types.png")
```

### Relationship Matrix

```python
from veritasreason.visualization import KGVisualizer

viz = KGVisualizer()

fig = viz.visualize_relationship_matrix(graph, output="interactive", file_path="relationship_matrix.html")
```

## Ontology Visualization

### Hierarchy Visualization

```python
from veritasreason.visualization import OntologyVisualizer

viz = OntologyVisualizer(color_scheme="default")

ontology = {
    "classes": [
        {"name": "Thing", "parent": None},
        {"name": "Person", "parent": "Thing"},
        {"name": "Employee", "parent": "Person"},
        {"name": "Manager", "parent": "Employee"}
    ]
}

# Interactive hierarchy
fig = viz.visualize_hierarchy(ontology, output="interactive")

# Save to file
viz.visualize_hierarchy(ontology, output="html", file_path="hierarchy.html")
viz.visualize_hierarchy(ontology, output="dot", file_path="hierarchy.dot")  # Graphviz format
```

### Property Graph Visualization

```python
from veritasreason.visualization import OntologyVisualizer

viz = OntologyVisualizer()

ontology = {
    "classes": [
        {"name": "Person", "properties": ["name", "age"]},
        {"name": "Organization", "properties": ["name", "founded"]}
    ],
    "properties": [
        {"name": "name", "domain": "Person", "range": "string"},
        {"name": "age", "domain": "Person", "range": "integer"},
        {"name": "founded", "domain": "Organization", "range": "date"}
    ]
}

fig = viz.visualize_properties(ontology, output="interactive", file_path="properties.html")
```

### Structure Network

```python
from veritasreason.visualization import OntologyVisualizer

viz = OntologyVisualizer()

fig = viz.visualize_structure(ontology, output="interactive", file_path="structure.html")
```

### Class-Property Matrix

```python
from veritasreason.visualization import OntologyVisualizer

viz = OntologyVisualizer()

fig = viz.visualize_class_property_matrix(ontology, output="interactive", file_path="matrix.png")
```

### Metrics Dashboard

```python
from veritasreason.visualization import OntologyVisualizer

viz = OntologyVisualizer()

fig = viz.visualize_metrics(ontology, output="interactive", file_path="metrics.html")
```

## Embedding Visualization

### 2D Projection

```python
from veritasreason.visualization import EmbeddingVisualizer
import numpy as np

viz = EmbeddingVisualizer(color_scheme="vibrant", point_size=8)

# Generate embeddings
embeddings = np.random.rand(1000, 768)
labels = [f"class_{i % 10}" for i in range(1000)]

# UMAP projection
fig = viz.visualize_2d_projection(
    embeddings, 
    labels, 
    method="umap",
    output="interactive",
    file_path="umap_2d.html"
)

# t-SNE projection
fig = viz.visualize_2d_projection(
    embeddings,
    labels,
    method="tsne",
    output="interactive",
    file_path="tsne_2d.html",
    perplexity=30
)

# PCA projection
fig = viz.visualize_2d_projection(
    embeddings,
    labels,
    method="pca",
    output="interactive",
    file_path="pca_2d.html"
)
```

### 3D Projection

```python
from veritasreason.visualization import EmbeddingVisualizer
import numpy as np

viz = EmbeddingVisualizer()

embeddings = np.random.rand(500, 768)
labels = [f"label_{i}" for i in range(500)]

# 3D UMAP
fig = viz.visualize_3d_projection(
    embeddings,
    labels,
    method="umap",
    output="interactive",
    file_path="umap_3d.html"
)

# 3D t-SNE
fig = viz.visualize_3d_projection(
    embeddings,
    labels,
    method="tsne",
    output="interactive",
    file_path="tsne_3d.html"
)
```

### Similarity Heatmap

```python
from veritasreason.visualization import EmbeddingVisualizer
import numpy as np

viz = EmbeddingVisualizer()

embeddings = np.random.rand(100, 768)
labels = [f"item_{i}" for i in range(100)]

fig = viz.visualize_similarity_heatmap(
    embeddings,
    labels,
    output="interactive",
    file_path="similarity_heatmap.html"
)
```

### Clustering Visualization

```python
from veritasreason.visualization import EmbeddingVisualizer
import numpy as np

viz = EmbeddingVisualizer()

embeddings = np.random.rand(1000, 768)
cluster_labels = [i % 5 for i in range(1000)]  # 5 clusters

fig = viz.visualize_clustering(
    embeddings,
    cluster_labels,
    method="umap",
    output="interactive",
    file_path="clusters.html"
)
```

### Multi-Modal Comparison

```python
from veritasreason.visualization import EmbeddingVisualizer
import numpy as np

viz = EmbeddingVisualizer()

text_embeddings = np.random.rand(100, 768)
image_embeddings = np.random.rand(100, 768)
audio_embeddings = np.random.rand(100, 768)

fig = viz.visualize_multimodal_comparison(
    text_embeddings,
    image_embeddings,
    audio_embeddings,
    output="interactive",
    file_path="multimodal.html"
)
```

## Semantic Network Visualization

### Network Structure

```python
from veritasreason.visualization import SemanticNetworkVisualizer

viz = SemanticNetworkVisualizer(color_scheme="vibrant")

semantic_network = {
    "nodes": [
        {"id": "n1", "label": "Node 1", "type": "Entity"},
        {"id": "n2", "label": "Node 2", "type": "Entity"}
    ],
    "edges": [
        {"source": "n1", "target": "n2", "label": "related_to"}
    ]
}

fig = viz.visualize_network(semantic_network, output="interactive", file_path="semantic_network.html")
```

### Node Type Distribution

```python
from veritasreason.visualization import SemanticNetworkVisualizer

viz = SemanticNetworkVisualizer()

fig = viz.visualize_node_types(semantic_network, output="interactive", file_path="node_types.png")
```

### Edge Type Distribution

```python
from veritasreason.visualization import SemanticNetworkVisualizer

viz = SemanticNetworkVisualizer()

fig = viz.visualize_edge_types(semantic_network, output="interactive", file_path="edge_types.png")
```

## Analytics Visualization

### Centrality Rankings

```python
from veritasreason.visualization import AnalyticsVisualizer

viz = AnalyticsVisualizer()

centrality = {
    "node1": 0.9,
    "node2": 0.7,
    "node3": 0.5,
    "node4": 0.3
}

fig = viz.visualize_centrality_rankings(
    centrality,
    centrality_type="degree",
    top_n=20,
    output="interactive",
    file_path="centrality_rankings.html"
)
```

### Community Structure

```python
from veritasreason.visualization import AnalyticsVisualizer

viz = AnalyticsVisualizer()

graph = {
    "entities": [...],
    "relationships": [...]
}
communities = {
    "node_assignments": {...},
    "num_communities": 5
}

fig = viz.visualize_community_structure(
    graph,
    communities,
    output="interactive",
    file_path="communities.html"
)
```

### Connectivity Analysis

```python
from veritasreason.visualization import AnalyticsVisualizer

viz = AnalyticsVisualizer()

connectivity = {
    "components": [
        {"nodes": ["n1", "n2"], "size": 2},
        {"nodes": ["n3"], "size": 1}
    ],
    "density": 0.5,
    "clustering_coefficient": 0.3
}

fig = viz.visualize_connectivity(
    connectivity,
    output="interactive",
    file_path="connectivity.html"
)
```

### Degree Distribution

```python
from veritasreason.visualization import AnalyticsVisualizer

viz = AnalyticsVisualizer()

graph = {
    "entities": [...],
    "relationships": [...]
}

fig = viz.visualize_degree_distribution(
    graph,
    output="interactive",
    file_path="degree_distribution.png"
)
```

### Metrics Dashboard

```python
from veritasreason.visualization import AnalyticsVisualizer

viz = AnalyticsVisualizer()

metrics = {
    "num_nodes": 1000,
    "num_edges": 5000,
    "density": 0.01,
    "clustering_coefficient": 0.3
}

fig = viz.visualize_metrics_dashboard(
    metrics,
    output="interactive",
    file_path="analytics_dashboard.html"
)
```

## Temporal Visualization

### Timeline Visualization

```python
from veritasreason.visualization import TemporalVisualizer

viz = TemporalVisualizer()

temporal_data = {
    "events": [
        {"timestamp": "2023-01-01", "type": "creation", "label": "Entity created"},
        {"timestamp": "2023-02-01", "type": "update", "label": "Entity updated"},
        {"timestamp": "2023-03-01", "type": "deletion", "label": "Entity deleted"}
    ],
    "timestamps": ["2023-01-01", "2023-02-01", "2023-03-01"]
}

fig = viz.visualize_timeline(
    temporal_data,
    output="interactive",
    file_path="timeline.html"
)
```

### Temporal Patterns

```python
from veritasreason.visualization import TemporalVisualizer

viz = TemporalVisualizer()

patterns = {
    "trends": [...],
    "cycles": [...],
    "anomalies": [...]
}

fig = viz.visualize_temporal_patterns(
    patterns,
    output="interactive",
    file_path="patterns.html"
)
```

### Snapshot Comparison

```python
from veritasreason.visualization import TemporalVisualizer

viz = TemporalVisualizer()

snapshots = [
    {"timestamp": "2023-01-01", "graph": {...}},
    {"timestamp": "2023-02-01", "graph": {...}},
    {"timestamp": "2023-03-01", "graph": {...}}
]

fig = viz.visualize_snapshot_comparison(
    snapshots,
    output="interactive",
    file_path="snapshot_comparison.html"
)
```

### Metrics Evolution

```python
from veritasreason.visualization import TemporalVisualizer

viz = TemporalVisualizer()

metrics_history = [
    {"num_nodes": 100, "num_edges": 200},
    {"num_nodes": 150, "num_edges": 300},
    {"num_nodes": 200, "num_edges": 400}
]
timestamps = ["2023-01-01", "2023-02-01", "2023-03-01"]

fig = viz.visualize_metrics_evolution(
    metrics_history,
    timestamps,
    output="interactive",
    file_path="evolution.html"
)
```

## Layout Algorithms

### Force-Directed Layout

```python
from veritasreason.visualization import KGVisualizer

# Force-directed layout (default)
viz = KGVisualizer(layout="force", k=1.0, iterations=50)

fig = viz.visualize_network(graph, output="interactive")
```

### Hierarchical Layout

```python
from veritasreason.visualization import KGVisualizer

# Hierarchical layout
viz = KGVisualizer(
    layout="hierarchical",
    vertical_spacing=2.0
)

fig = viz.visualize_network(graph, output="interactive")
```

### Circular Layout

```python
from veritasreason.visualization import KGVisualizer

# Circular layout
viz = KGVisualizer(
    layout="circular",
    radius=1.5
)

fig = viz.visualize_network(graph, output="interactive")
```

## Color Schemes

### Available Color Schemes

```python
from veritasreason.visualization import KGVisualizer

# Default color scheme
viz_default = KGVisualizer(color_scheme="default")

# Vibrant color scheme
viz_vibrant = KGVisualizer(color_scheme="vibrant")

# Pastel color scheme
viz_pastel = KGVisualizer(color_scheme="pastel")

# Dark color scheme
viz_dark = KGVisualizer(color_scheme="dark")

# Light color scheme
viz_light = KGVisualizer(color_scheme="light")

# Colorblind-friendly color scheme
viz_colorblind = KGVisualizer(color_scheme="colorblind")
```

## Export Formats

### HTML Export

```python
from veritasreason.visualization import KGVisualizer

viz = KGVisualizer()

# Export to HTML
viz.visualize_network(graph, output="html", file_path="network.html")
```

### PNG Export

```python
from veritasreason.visualization import KGVisualizer

viz = KGVisualizer()

# Export to PNG
viz.visualize_network(
    graph,
    output="png",
    file_path="network.png",
    width=1200,
    height=800
)
```

### SVG Export

```python
from veritasreason.visualization import KGVisualizer

viz = KGVisualizer()

# Export to SVG
viz.visualize_network(graph, output="svg", file_path="network.svg")
```

### PDF Export

```python
from veritasreason.visualization import KGVisualizer

viz = KGVisualizer()

# Export to PDF
viz.visualize_network(graph, output="pdf", file_path="network.pdf")
```

## Algorithms and Methods

### Knowledge Graph Visualization Algorithms

#### Network Graph Construction
**Algorithm**: Entity-to-node mapping, relationship-to-edge mapping
**Time Complexity**: O(n + m) where n = entities, m = relationships
**Space Complexity**: O(n + m)

```python
# Network graph construction
viz = KGVisualizer()
fig = viz.visualize_network(graph)
```

#### Layout Computation
**Algorithm**: Force-directed spring layout (NetworkX spring_layout or basic force-directed)
**Time Complexity**: O(n² * iterations) for basic, O(n log n) for NetworkX
**Space Complexity**: O(n)

```python
# Force-directed layout
viz = KGVisualizer(layout="force", k=1.0, iterations=50)
fig = viz.visualize_network(graph)
```

#### Community Coloring
**Algorithm**: Community assignment mapping, color palette generation
**Time Complexity**: O(n)
**Space Complexity**: O(n)

```python
# Community visualization
viz = KGVisualizer()
fig = viz.visualize_communities(graph, communities)
```

### Embedding Visualization Algorithms

#### Dimensionality Reduction - UMAP
**Algorithm**: Uniform Manifold Approximation and Projection
**Time Complexity**: O(n * log(n) * d) where n = samples, d = dimensions
**Space Complexity**: O(n * d)

```python
# UMAP 2D projection
viz = EmbeddingVisualizer()
fig = viz.visualize_2d_projection(embeddings, labels, method="umap", n_neighbors=15)
```

#### Dimensionality Reduction - t-SNE
**Algorithm**: t-distributed Stochastic Neighbor Embedding
**Time Complexity**: O(n² * d)
**Space Complexity**: O(n²)

```python
# t-SNE 2D projection
viz = EmbeddingVisualizer()
fig = viz.visualize_2d_projection(embeddings, labels, method="tsne", perplexity=30)
```

#### Dimensionality Reduction - PCA
**Algorithm**: Principal Component Analysis
**Time Complexity**: O(n * d²)
**Space Complexity**: O(d²)

```python
# PCA 2D projection
viz = EmbeddingVisualizer()
fig = viz.visualize_2d_projection(embeddings, labels, method="pca", n_components=2)
```

#### Similarity Heatmap
**Algorithm**: Pairwise similarity calculation (cosine similarity)
**Time Complexity**: O(n² * d)
**Space Complexity**: O(n²)

```python
# Similarity heatmap
viz = EmbeddingVisualizer()
fig = viz.visualize_similarity_heatmap(embeddings, labels)
```

### Layout Algorithms

#### Force-Directed Spring Layout
**Algorithm**: Iterative force calculation with repulsive/attractive forces
**Time Complexity**: O(n² * iterations)
**Space Complexity**: O(n)

```python
# Force-directed layout
viz = KGVisualizer(layout="force", k=1.0, iterations=50)
```

#### Hierarchical Tree Layout
**Algorithm**: BFS traversal for level assignment
**Time Complexity**: O(n + m) where n = nodes, m = edges
**Space Complexity**: O(n)

```python
# Hierarchical layout
viz = KGVisualizer(layout="hierarchical", vertical_spacing=2.0)
```

#### Circular Layout
**Algorithm**: Circular positioning (angle = 2π * index / node_count)
**Time Complexity**: O(n)
**Space Complexity**: O(n)

```python
# Circular layout
viz = KGVisualizer(layout="circular", radius=1.5)
```

### Methods

#### KGVisualizer Methods
- `visualize_network(graph, output, file_path, **options)`: Visualize knowledge graph network
- `visualize_communities(graph, communities, output, file_path, **options)`: Visualize communities
- `visualize_centrality(graph, centrality, centrality_type, output, file_path, **options)`: Visualize centrality
- `visualize_entity_types(graph, output, file_path, **options)`: Visualize entity type distribution
- `visualize_relationship_matrix(graph, output, file_path, **options)`: Visualize relationship matrix

#### OntologyVisualizer Methods
- `visualize_hierarchy(ontology, output, file_path, **options)`: Visualize class hierarchy
- `visualize_properties(ontology, output, file_path, **options)`: Visualize property graph
- `visualize_structure(ontology, output, file_path, **options)`: Visualize ontology structure
- `visualize_class_property_matrix(ontology, output, file_path, **options)`: Visualize class-property matrix
- `visualize_metrics(ontology, output, file_path, **options)`: Visualize ontology metrics

#### EmbeddingVisualizer Methods
- `visualize_2d_projection(embeddings, labels, method, output, file_path, **options)`: 2D projection
- `visualize_3d_projection(embeddings, labels, method, output, file_path, **options)`: 3D projection
- `visualize_similarity_heatmap(embeddings, labels, output, file_path, **options)`: Similarity heatmap
- `visualize_clustering(embeddings, cluster_labels, method, output, file_path, **options)`: Clustering visualization
- `visualize_multimodal_comparison(text_emb, image_emb, audio_emb, output, file_path, **options)`: Multi-modal comparison

#### SemanticNetworkVisualizer Methods
- `visualize_network(semantic_network, output, file_path, **options)`: Visualize semantic network
- `visualize_node_types(semantic_network, output, file_path, **options)`: Node type distribution
- `visualize_edge_types(semantic_network, output, file_path, **options)`: Edge type distribution

#### AnalyticsVisualizer Methods
- `visualize_centrality_rankings(centrality, centrality_type, top_n, output, file_path, **options)`: Centrality rankings
- `visualize_community_structure(graph, communities, output, file_path, **options)`: Community structure
- `visualize_connectivity(connectivity, output, file_path, **options)`: Connectivity analysis
- `visualize_degree_distribution(graph, output, file_path, **options)`: Degree distribution
- `visualize_metrics_dashboard(metrics, output, file_path, **options)`: Metrics dashboard
- `visualize_centrality_comparison(centrality_results, top_n, output, file_path, **options)`: Compare multiple centralities

#### TemporalVisualizer Methods
- `visualize_timeline(temporal_data, output, file_path, **options)`: Event timeline
- `visualize_temporal_patterns(patterns, output, file_path, **options)`: Temporal patterns
- `visualize_snapshot_comparison(snapshots, output, file_path, **options)`: Snapshot comparison
- `visualize_version_history(version_history, output, file_path, **options)`: Version history
- `visualize_metrics_evolution(metrics_history, timestamps, output, file_path, **options)`: Metrics over time

#### Convenience Functions
- `visualize_kg(graph, output, file_path, method, **options)`: Knowledge graph visualization wrapper
- `visualize_ontology(ontology, output, file_path, method, **options)`: Ontology visualization wrapper
- `visualize_embeddings(embeddings, labels, output, file_path, method, **options)`: Embedding visualization wrapper
- `visualize_semantic_network(semantic_network, output, file_path, method, **options)`: Semantic network visualization wrapper
- `visualize_analytics(analytics_data, output, file_path, method, **options)`: Analytics visualization wrapper
- `visualize_temporal(temporal_data, output, file_path, method, **options)`: Temporal visualization wrapper
- `get_visualization_method(task, method_name)`: Get visualization method by task and name
- `list_available_methods(task)`: List registered visualization methods

## Configuration

### Environment Variables

```bash
# Visualization configuration
export VISUALIZATION_DEFAULT_LAYOUT=force
export VISUALIZATION_COLOR_SCHEME=default
export VISUALIZATION_OUTPUT_FORMAT=interactive
export VISUALIZATION_NODE_SIZE=10
export VISUALIZATION_EDGE_WIDTH=1
export VISUALIZATION_POINT_SIZE=5

# Dimensionality reduction
export VISUALIZATION_DIMENSION_REDUCTION_METHOD=umap
export VISUALIZATION_UMAP_N_NEIGHBORS=15
export VISUALIZATION_TSNE_PERPLEXITY=30.0
export VISUALIZATION_PCA_N_COMPONENTS=2

# Layout parameters
export VISUALIZATION_FORCE_LAYOUT_K=1.0
export VISUALIZATION_FORCE_LAYOUT_ITERATIONS=50
export VISUALIZATION_HIERARCHICAL_VERTICAL_SPACING=2.0
export VISUALIZATION_CIRCULAR_RADIUS=1.5
```

### Programmatic Configuration

```python
from veritasreason.visualization.config import visualization_config

# Get configuration
layout = visualization_config.get("default_layout", default="force")
color_scheme = visualization_config.get("color_scheme", default="default")

# Set configuration
visualization_config.set("default_layout", "hierarchical")
visualization_config.set("color_scheme", "vibrant")

# Update with dictionary
visualization_config.update({
    "default_layout": "force",
    "color_scheme": "vibrant",
    "node_size": 15
})
```

### Configuration File (YAML)

```yaml
# config.yaml
visualization:
  default_layout: force
  color_scheme: default
  output_format: interactive
  node_size: 10
  edge_width: 1
  point_size: 5
  dimension_reduction_method: umap
  umap_n_neighbors: 15
  tsne_perplexity: 30.0
  pca_n_components: 2
  force_layout_k: 1.0
  force_layout_iterations: 50
  hierarchical_vertical_spacing: 2.0
  circular_radius: 1.5
```

### Method-Specific Configuration

```python
from veritasreason.visualization.config import visualization_config

# Set method-specific configuration
visualization_config.set_method_config("visualize_kg", {
    "layout": "force",
    "color_scheme": "vibrant",
    "node_size": 15
})

# Get method-specific configuration
method_config = visualization_config.get_method_config("visualize_kg")
```

## Advanced Examples

### Complete Visualization Pipeline

```python
from veritasreason.visualization import (
    visualize_kg,
    visualize_embeddings,
    visualize_ontology,
    visualize_semantic_network,
    visualize_analytics,
    visualize_temporal,
    list_available_methods
)
import numpy as np

# 1. Knowledge graph visualization
graph = {
    "entities": [...],
    "relationships": [...]
}
fig_kg = visualize_kg(graph, output="html", file_path="kg.html")

# 2. Embedding visualization
embeddings = np.random.rand(1000, 768)
labels = [f"label_{i}" for i in range(1000)]
fig_emb = visualize_embeddings(embeddings, labels, method="2d_projection", 
                               output="html", file_path="embeddings.html")

# 3. Ontology visualization
ontology = {"classes": [...], "properties": [...]}
fig_ont = visualize_ontology(ontology, method="hierarchy", 
                            output="html", file_path="ontology.html")

# 4. Analytics visualization
fig_analytics = visualize_analytics({"centrality": {}}, method="centrality", 
                                  output="html", file_path="analytics.html")
```

### Custom Method Registration

```python
from veritasreason.visualization.registry import method_registry

def custom_kg_visualization(graph, output="interactive", file_path=None, **options):
    """Custom knowledge graph visualization method."""
    # Custom implementation
    pass

# Register custom method
method_registry.register("kg", "custom_method", custom_kg_visualization)

# Use custom method
from veritasreason.visualization import visualize_kg
fig = visualize_kg(graph, method="custom_method", output="interactive")
```

### Multi-Format Export

```python
from veritasreason.visualization import KGVisualizer

viz = KGVisualizer()

graph = {...}

# Export to multiple formats
formats = ["html", "png", "svg", "pdf"]
for fmt in formats:
    viz.visualize_network(
        graph,
        output=fmt,
        file_path=f"network.{fmt}",
        width=1200,
        height=800
    )
```

### Batch Visualization

```python
from veritasreason.visualization import EmbeddingVisualizer
import numpy as np

viz = EmbeddingVisualizer()

# Visualize multiple embedding sets
embedding_sets = [
    (np.random.rand(100, 768), "set1"),
    (np.random.rand(100, 768), "set2"),
    (np.random.rand(100, 768), "set3")
]

for embeddings, name in embedding_sets:
    labels = [f"{name}_{i}" for i in range(len(embeddings))]
    fig = viz.visualize_2d_projection(
        embeddings,
        labels,
        method="umap",
        output="html",
        file_path=f"{name}_projection.html"
    )
```

## Best Practices

### Performance Optimization

1. **Use appropriate layout algorithms**: Force-directed for small graphs (< 1000 nodes), hierarchical for tree structures, circular for small networks
2. **Optimize dimensionality reduction**: Use PCA for fast projection, UMAP for better structure preservation, t-SNE for small datasets
3. **Batch processing**: Process large datasets in batches to avoid memory issues
4. **Caching**: Cache layout computations for repeated visualizations

### Visualization Quality

1. **Choose appropriate color schemes**: Use colorblind-friendly schemes for accessibility
2. **Node/edge sizing**: Adjust node and edge sizes based on graph density
3. **Interactive vs static**: Use interactive HTML for exploration, static PNG/SVG for publication
4. **Layout parameters**: Tune layout parameters (k, iterations, spacing) for better visualizations

### Code Organization

1. **Use convenience functions**: Prefer convenience functions for simple use cases
2. **Use classes directly**: Use visualizer classes for advanced customization
3. **Configuration management**: Use configuration files for consistent settings
4. **Method registry**: Register custom methods for reusable visualizations

### Error Handling

1. **Validate inputs**: Check graph structure, embedding dimensions, etc.
2. **Handle missing dependencies**: Gracefully handle missing optional dependencies (UMAP, Graphviz)
3. **File path validation**: Validate file paths before export
4. **Error messages**: Provide clear error messages for debugging


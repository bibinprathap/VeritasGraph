# Visualization

> **Comprehensive visualization suite for Knowledge Graphs, Ontologies, Embeddings, and Temporal data.**

---

## 🎯 Overview

<div class="grid cards" markdown>

-   :material-graph:{ .lg .middle } **KG Visualization**

    ---

    Interactive network graphs with Force-directed, Hierarchical, and Circular layouts

-   :material-file-tree:{ .lg .middle } **Ontology View**

    ---

    Visualize class hierarchies, property domains/ranges, and taxonomy trees

-   :material-chart-scatter-plot:{ .lg .middle } **Embedding Projector**

    ---

    2D/3D visualization of vector embeddings using UMAP, t-SNE, and PCA

-   :material-clock-time-four-outline:{ .lg .middle } **Temporal Analysis**

    ---

    Timeline views and graph evolution visualization

-   :material-chart-bar:{ .lg .middle } **Analytics Dashboards**

    ---

    Visual dashboards for centrality, community structure, and connectivity

-   :material-export:{ .lg .middle } **Multi-Format Export**

    ---

    Export to HTML (interactive), PNG, SVG, PDF, and JSON

</div>

!!! tip "When to Use"
    - **Exploration**: Interactively explore graph connections and clusters
    - **Reporting**: Generate static charts for reports and presentations
    - **Debugging**: Visually inspect graph structure and disconnected components
    - **Analysis**: Identify patterns, outliers, and trends in data

---

## ⚙️ Algorithms Used

### Layout Algorithms

The visualization module uses various layout algorithms:

- **Force-Directed**: Simulates physical forces (repulsion between nodes, springs for edges) to find equilibrium
- **Hierarchical**: Tree-based layout for taxonomies and directed acyclic graphs (DAGs)
- **Circular**: Arranges nodes in a circle, useful for analyzing interconnectivity
- **Community-Based**: Groups nodes by community (Louvain/Leiden) and separates clusters

### Dimensionality Reduction

The module supports multiple dimensionality reduction techniques:

- **UMAP**: Uniform Manifold Approximation and Projection - Preserves global structure better than t-SNE
- **t-SNE**: t-Distributed Stochastic Neighbor Embedding - Good for local clustering
- **PCA**: Principal Component Analysis - Linear projection for variance maximization

### Analytics Visualization
- **Centrality Sizing**: Node size proportional to Degree/Betweenness/PageRank.
- **Heatmaps**: Matrix visualization for adjacency or similarity.
- **Sankey Diagrams**: Flow visualization for lineage or process steps.

---

## Main Classes

### KGVisualizer

Visualizes Knowledge Graph structure and communities.

**Methods:**

| Method | Description |
|--------|-------------|
| `visualize_network(graph)` | Standard network plot |
| `visualize_communities(graph)` | Color by community |
| `visualize_centrality(graph, centrality, centrality_type)` | Size/color by centrality |
| `visualize_entity_types(graph)` | Entity type distribution |
| `visualize_relationship_matrix(graph)` | Relationship frequency heatmap |

**Example:**

```python
from veritasreason.visualization import KGVisualizer

viz = KGVisualizer(layout="force", height=800)
fig = viz.visualize_network(kg, output="interactive")
fig.write_html("graph.html")
```

### OntologyVisualizer

Visualizes schema and taxonomy.

**Methods:**

| Method | Description |
|--------|-------------|
| `visualize_hierarchy(ontology)` | Tree view of classes |
| `visualize_properties(ontology)` | Property domain/range graph |
| `visualize_structure(ontology)` | Class-property network |
| `visualize_class_property_matrix(ontology)` | Class vs property heatmap |
| `visualize_metrics(ontology)` | Metrics dashboard |
| `visualize_semantic_model(model)` | Visualize semantic model/network |

### EmbeddingVisualizer

Project high-dimensional vectors to 2D/3D.

**Methods:**

| Method | Description | Algorithm |
|--------|-------------|-----------|
| `visualize_2d_projection(embeddings, labels, method)` | 2D Scatter plot | UMAP/t-SNE/PCA |
| `visualize_3d_projection(embeddings, labels, method)` | 3D Scatter plot | UMAP/t-SNE/PCA |
| `visualize_similarity_heatmap(embeddings, labels)` | Pairwise similarity | Cosine |
| `visualize_clustering(embeddings, cluster_labels, method)` | Colored by cluster | UMAP/t-SNE/PCA |
| `visualize_multimodal_comparison(text_emb, image_emb, audio_emb)` | Compare modalities | UMAP/PCA |

**Example:**

```python
from veritasreason.visualization import EmbeddingVisualizer

viz = EmbeddingVisualizer()
viz.visualize_2d_projection(
    embeddings, 
    labels=labels, 
    method="umap",
    output="embeddings.html"
)
```

### SemanticNetworkVisualizer

Visualizes semantic network structure and distributions.

**Methods:**

| Method | Description |
|--------|-------------|
| `visualize_network(semantic_network)` | Network visualization |
| `visualize_node_types(semantic_network)` | Node type distribution |
| `visualize_edge_types(semantic_network)` | Edge type distribution |

### AnalyticsVisualizer

Visualizes graph analytics results.

**Methods:**

| Method | Description |
|--------|-------------|
| `visualize_centrality_rankings(centrality, centrality_type, top_n)` | Top-k bar chart |
| `visualize_community_structure(graph, communities)` | Community network |
| `visualize_connectivity(connectivity)` | Components and sizes |
| `visualize_degree_distribution(graph)` | Degree histogram |
| `visualize_metrics_dashboard(metrics)` | Metrics dashboard |
| `visualize_centrality_comparison(centrality_results, top_n)` | Grouped comparison |

### TemporalVisualizer

Visualizes time-series and graph evolution.

**Methods:**

| Method | Description |
|--------|-------------|
| `visualize_timeline(events)` | Event timeline |
| `visualize_temporal_patterns(patterns)` | Pattern durations |
| `visualize_snapshot_comparison(snapshots)` | Compare snapshots |
| `visualize_version_history(version_history)` | Version timeline |
| `visualize_metrics_evolution(metrics_history, timestamps)` | Metrics over time |

---

## Convenience Functions

```python
from veritasreason.visualization import (
    visualize_kg,
    visualize_embeddings,
    visualize_ontology,
    visualize_semantic_network,
    visualize_analytics,
    visualize_temporal,
    list_available_methods,
)

# One-line visualization
visualize_kg(kg, output="graph.html")
visualize_embeddings(embeddings, method="umap")
visualize_ontology(ontology, method="hierarchy")
visualize_semantic_network(semantic_network)
visualize_analytics({"centrality": centrality}, method="centrality")
visualize_temporal(temporal_data, method="timeline")
list_available_methods()
```

---

## Configuration

### Environment Variables

```bash
export VISUALIZATION_DEFAULT_LAYOUT=force
export VISUALIZATION_COLOR_SCHEME=vibrant
export VISUALIZATION_OUTPUT_FORMAT=interactive
```

### YAML Configuration

```yaml
visualization:
  layout:
    algorithm: force
    iterations: 50
    
  style:
    node_size: 10
    edge_width: 1
    color_scheme: "vibrant" # vibrant, pastel, dark
    
  export:
    width: 1200
    height: 800
    scale: 2.0
```

---

## Integration Examples

### Exploratory Data Analysis (EDA)

```python
from veritasreason.kg import GraphBuilder
from veritasreason.visualization import KGVisualizer, AnalyticsVisualizer

# 1. Build Knowledge Graph
builder = GraphBuilder()
kg = builder.build(sources=sample_data)

# 2. Visualize Structure
kg_viz = KGVisualizer()
kg_viz.visualize_network(kg, output="structure.html")

# 3. Visualize Analytics
analytics_viz = AnalyticsVisualizer()
centrality = {"rankings": [{"node": "A", "score": 0.9}, {"node": "B", "score": 0.7}]}
analytics_viz.visualize_centrality_rankings(centrality, centrality_type="degree", top_n=10, output="centrality.png")
analytics_viz.visualize_degree_distribution(kg, output="degree_dist.png")
```

---

## Best Practices

1.  **Filter First**: Don't try to visualize 1M nodes. Filter to a subgraph of <5000 nodes for readability.
2.  **Use Interactive**: Interactive HTML plots (Plotly) allow zooming and hovering, which is essential for dense graphs.
3.  **Color Meaningfully**: Use color to represent node types or communities, not just random assignment.
4.  **Size by Importance**: Map node size to centrality (e.g., PageRank) to highlight important entities.

---

## See Also
- [Knowledge Graph Module](kg.md) - The data source
- [Embeddings Module](embeddings.md) - Source for vector visualizations
- [Ontology Module](ontology.md) - Source for hierarchy visualizations

## Cookbook

Interactive tutorials to learn graph visualization:

- **[Visualization](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/introduction/16_Visualization.ipynb)**: Basic graph visualization techniques
  - **Topics**: Graph visualization, network diagrams, basic plotting
  - **Difficulty**: Beginner
  - **Use Cases**: Visualizing knowledge graphs, understanding graph structure

- **[Complete Visualization Suite](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/advanced/03_Complete_Visualization_Suite.ipynb)**: Creating interactive, publication-ready visualizations
  - **Topics**: PyVis, NetworkX, D3.js, interactive visualizations, publication-ready graphics
  - **Difficulty**: Intermediate
  - **Use Cases**: Advanced visualizations, presentations, publications

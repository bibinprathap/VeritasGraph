"""
Visualization Module

This module provides comprehensive visualization capabilities for all knowledge artifacts
created by the VeritasReason framework, including knowledge graphs, ontologies, embeddings,
semantic networks, analytics results, and temporal graphs with interactive
and static output formats.

Algorithms Used:

Knowledge Graph Visualization:
    - Network Graph Construction: Entity-to-node mapping, relationship-to-edge mapping, node/edge attribute extraction, graph structure building
    - Node/Edge Extraction: Entity ID/label/type extraction, relationship source/target/label extraction, metadata attachment, property extraction
    - Layout Computation: Force-directed layout (NetworkX spring_layout or basic force-directed), hierarchical layout (tree structure, level assignment), circular layout (circular positioning with radius calculation)
    - Community Coloring: Community assignment mapping, color palette generation per community, node color assignment based on community ID, color scheme application
    - Centrality-Based Sizing: Centrality score normalization, node size calculation (base_size * (1 + centrality_factor * centrality_score)), edge width calculation based on relationship strength
    - Entity/Relationship Distribution: Type frequency counting, histogram generation, bar chart construction, distribution visualization

Ontology Visualization:
    - Hierarchy Tree Construction: Parent-child relationship extraction, tree structure building, root node identification, level assignment (BFS traversal), tree depth calculation
    - Property Graph Visualization: Property-to-node mapping, domain/range relationship extraction, property type classification, property graph layout
    - Structure Network: Class-to-class relationship extraction, property-to-class mapping, ontology structure graph construction, network layout computation
    - Class-Property Matrix: Class-property relationship matrix construction, binary matrix generation (1 if class has property, 0 otherwise), heatmap visualization, matrix normalization
    - Metrics Dashboard: Ontology metrics calculation (class count, property count, depth, breadth), gauge indicator generation, score visualization, metric comparison

Embedding Visualization:
    - Dimensionality Reduction: UMAP (uniform manifold approximation and projection with n_neighbors, min_dist parameters), t-SNE (t-distributed stochastic neighbor embedding with perplexity parameter), PCA (principal component analysis with variance maximization), dimension reduction from high-D to 2D/3D
    - Similarity Heatmap: Pairwise similarity calculation (cosine similarity, dot product, Euclidean distance), similarity matrix construction, heatmap generation with color mapping, hierarchical clustering (optional)
    - Clustering Visualization: Cluster label assignment, cluster color mapping, cluster centroid calculation, cluster boundary visualization, cluster size distribution
    - Multi-Modal Comparison: Multi-modal embedding alignment, cross-modal similarity calculation, alignment visualization, modality comparison charts

Semantic Network Visualization:
    - Network Structure Visualization: Node/edge extraction from semantic network, graph construction, layout computation, network rendering
    - Type Distribution: Node type frequency counting, edge type frequency counting, distribution chart generation, type-based color assignment
    - Relationship Patterns: Relationship frequency analysis, pattern detection, relationship matrix construction, pattern visualization

Analytics Visualization:
    - Centrality Rankings: Centrality score extraction (degree, betweenness, closeness, eigenvector), score normalization, ranking calculation (argsort descending), top-k selection, bar chart generation
    - Community Structure: Community assignment extraction, community size calculation, community color mapping, community network visualization, inter-community edge analysis
    - Connectivity Analysis: Component detection (connected component analysis), component size calculation, component visualization, connectivity metrics (density, clustering coefficient)
    - Degree Distribution: Degree calculation per node, degree frequency counting, histogram generation, degree distribution fitting (power-law, exponential), distribution visualization

Temporal Visualization:
    - Timeline Construction: Event timestamp extraction, event type classification, timeline axis generation, event positioning on timeline, event grouping by type
    - Pattern Visualization: Temporal pattern detection (trends, cycles, anomalies), pattern extraction, pattern visualization, pattern annotation
    - Snapshot Comparison: Graph snapshot extraction at time points, snapshot difference calculation, change detection (added/removed entities/relationships), comparison visualization, diff highlighting
    - Evolution Analysis: Metrics evolution tracking over time, time series construction, trend analysis, evolution visualization, change rate calculation

Layout Algorithms:
    - Force-Directed Spring Layout: NetworkX spring_layout (force-directed graph layout with repulsive/attractive forces), basic force-directed (iterative force calculation: repulsive forces between all nodes, attractive forces along edges, position update with cooling), k-parameter optimization (optimal distance), iteration-based convergence
    - Hierarchical Tree Layout: Tree structure construction, root identification, level assignment (BFS traversal), vertical spacing calculation, horizontal positioning (tree width distribution), Graphviz integration (when available)
    - Circular Layout: Circular positioning algorithm (angle = 2π * index / node_count), radius calculation, node positioning on circle, edge routing (straight lines or curves)

Color Schemes:
    - Color Palette Generation: Base color scheme selection (Default, Vibrant, Pastel, Dark, Light, Colorblind), color list generation (repeat colors if count > base colors), color interpolation (for smooth gradients)
    - Entity Type Coloring: Entity type-to-color mapping, color assignment per type, color scheme consistency, type color caching
    - Community Coloring: Community ID-to-color mapping, color assignment per community, distinct color generation for multiple communities, color scheme application
    - Color Scheme Management: Color scheme enumeration, color scheme lookup, color scheme switching, color scheme validation

Export Formats:
    - Plotly Export: HTML export (write_html with configurable options), PNG export (write_image with width/height/scale), SVG export (write_image with SVG format), PDF export (write_image with PDF format), JSON export (write_json for figure serialization)
    - Matplotlib Export: PNG export (savefig with DPI/bbox_inches), SVG export (savefig with SVG format), PDF export (savefig with PDF format), JPG export (savefig with JPG format), figure optimization
    - HTML Generation: HTML template construction, Plotly.js embedding, interactive figure embedding, standalone HTML generation, custom styling injection
    - Format Conversion: Format detection, format-specific export delegation, format validation, error handling per format

Key Features:
    - Interactive and static visualization outputs (HTML, PNG, SVG, PDF)
    - Knowledge graph network visualizations with multiple layout algorithms
    - Ontology hierarchy and structure visualizations
    - Embedding dimensionality reduction and clustering visualizations
    - Semantic network visualizations
    - Graph analytics visualizations (centrality, communities, connectivity)
    - Temporal graph timeline and evolution visualizations
    - Customizable color schemes and layout algorithms
    - Method registry for extensibility
    - Configuration management with environment variables and config files

Main Classes:
    - KGVisualizer: Knowledge graph network and community visualizations
    - OntologyVisualizer: Ontology hierarchy, properties, and structure visualizations
    - EmbeddingVisualizer: Vector embedding projections, similarity, and clustering
    - SemanticNetworkVisualizer: Semantic network structure and type distributions
    - AnalyticsVisualizer: Graph analytics, centrality rankings, and metrics dashboards
    - TemporalVisualizer: Temporal timeline, patterns, and snapshot comparisons
    - D3Visualizer: D3.js-based interactive visualizations for web dashboards

Convenience Functions:
    - visualize_kg: Knowledge graph visualization wrapper
    - visualize_ontology: Ontology visualization wrapper
    - visualize_embeddings: Embedding visualization wrapper
    - visualize_semantic_network: Semantic network visualization wrapper
    - visualize_analytics: Analytics visualization wrapper
    - visualize_temporal: Temporal visualization wrapper
    - get_visualization_method: Get visualization method by task and name
    - list_available_methods: List registered visualization methods

Example Usage:
    >>> from veritasreason.visualization import KGVisualizer, visualize_kg
    >>> # Using convenience functions
    >>> fig = visualize_kg(graph, output="interactive", method="default")
    >>> # Using classes directly
    >>> viz = KGVisualizer(layout="force", color_scheme="vibrant")
    >>> fig = viz.visualize_network(graph, output="interactive")
    >>> viz.visualize_communities(graph, communities, file_path="communities.html")
    >>> 
    >>> from veritasreason.visualization import EmbeddingVisualizer, visualize_embeddings
    >>> emb_viz = EmbeddingVisualizer()
    >>> fig = emb_viz.visualize_2d_projection(embeddings, labels, method="umap")
    >>> emb_viz.visualize_clustering(embeddings, cluster_labels, file_path="clusters.png")
    >>> 
    >>> from veritasreason.visualization import OntologyVisualizer, visualize_ontology
    >>> ont_viz = OntologyVisualizer()
    >>> fig = ont_viz.visualize_hierarchy(ontology, output="interactive")

Author: VeritasReason Contributors
License: MIT
"""

from .analytics_visualizer import AnalyticsVisualizer
from .config import VisualizationConfig, visualization_config
from .embedding_visualizer import EmbeddingVisualizer
from .kg_visualizer import KGVisualizer
from .methods import (
    get_visualization_method,
    list_available_methods,
    visualize_analytics,
    visualize_embeddings,
    visualize_kg,
    visualize_ontology,
    visualize_semantic_network,
    visualize_temporal,
)
from .ontology_visualizer import OntologyVisualizer
from .registry import MethodRegistry, method_registry
from .semantic_network_visualizer import SemanticNetworkVisualizer
from .temporal_visualizer import TemporalVisualizer

__all__ = [
    # Visualizers
    "KGVisualizer",
    "OntologyVisualizer",
    "EmbeddingVisualizer",
    "SemanticNetworkVisualizer",
    "AnalyticsVisualizer",
    "TemporalVisualizer",
    "D3Visualizer",
    # Convenience functions
    "visualize_kg",
    "visualize_ontology",
    "visualize_embeddings",
    "visualize_semantic_network",
    "visualize_analytics",
    "visualize_temporal",
    "get_visualization_method",
    "list_available_methods",
    # Configuration and registry
    "VisualizationConfig",
    "visualization_config",
    "MethodRegistry",
    "method_registry",
]

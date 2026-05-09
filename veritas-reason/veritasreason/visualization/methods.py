"""
Visualization Methods Module

This module provides all visualization methods as simple, reusable functions for
visualizing knowledge graphs, ontologies, embeddings, semantic networks,
analytics, and temporal data. It supports multiple approaches and integrates
with the method registry for extensibility.

Supported Methods:

Knowledge Graph Visualization:
    - "default": Default knowledge graph visualization using KGVisualizer
    - "network": Network graph visualization
    - "communities": Community visualization
    - "centrality": Centrality-based visualization

Ontology Visualization:
    - "default": Default ontology visualization using OntologyVisualizer
    - "hierarchy": Hierarchy tree visualization
    - "properties": Property graph visualization
    - "structure": Structure network visualization

Embedding Visualization:
    - "default": Default embedding visualization using EmbeddingVisualizer
    - "2d_projection": 2D dimensionality reduction projection
    - "3d_projection": 3D dimensionality reduction projection
    - "similarity": Similarity heatmap visualization
    - "clustering": Clustering visualization

Semantic Network Visualization:
    - "default": Default semantic network visualization using SemanticNetworkVisualizer
    - "network": Network structure visualization
    - "node_types": Node type distribution visualization
    - "edge_types": Edge type distribution visualization

Analytics Visualization:
    - "default": Default analytics visualization using AnalyticsVisualizer
    - "centrality": Centrality rankings visualization
    - "communities": Community structure visualization
    - "connectivity": Connectivity analysis visualization
    - "degree_distribution": Degree distribution visualization

Temporal Visualization:
    - "default": Default temporal visualization using TemporalVisualizer
    - "timeline": Timeline visualization
    - "patterns": Temporal pattern visualization
    - "snapshot_comparison": Snapshot comparison visualization
    - "evolution": Metrics evolution visualization

Algorithms Used:

Visualization Methods:
    - Method Dispatch: Registry-based method lookup and dispatch
    - Default Method Fallback: Fallback to default method if custom method not found
    - Configuration Integration: Configuration-based parameter setting
    - Global Instance Management: Singleton pattern for visualizer instances

Key Features:
    - Multiple visualization operation methods
    - Visualization with method dispatch
    - Method dispatchers with registry support
    - Custom method registration capability
    - Consistent interface across all methods

Main Functions:
    - visualize_kg: Knowledge graph visualization wrapper
    - visualize_ontology: Ontology visualization wrapper
    - visualize_embeddings: Embedding visualization wrapper
    - visualize_semantic_network: Semantic network visualization wrapper
    - visualize_analytics: Analytics visualization wrapper
    - visualize_temporal: Temporal visualization wrapper
    - get_visualization_method: Get visualization method by task and name
    - list_available_methods: List registered methods

Example Usage:
    >>> from veritasreason.visualization.methods import visualize_kg, visualize_embeddings
    >>> fig = visualize_kg(graph, output="interactive", method="default")
    >>> fig = visualize_embeddings(embeddings, labels, method="2d_projection", output="interactive")
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from .analytics_visualizer import AnalyticsVisualizer
from .config import visualization_config
from .embedding_visualizer import EmbeddingVisualizer
from .kg_visualizer import KGVisualizer
from .ontology_visualizer import OntologyVisualizer
from .registry import method_registry
from .semantic_network_visualizer import SemanticNetworkVisualizer
from .temporal_visualizer import TemporalVisualizer

# Global visualizer instances
_global_kg_visualizer: Optional[KGVisualizer] = None
_global_ontology_visualizer: Optional[OntologyVisualizer] = None
_global_embedding_visualizer: Optional[EmbeddingVisualizer] = None
_global_semantic_network_visualizer: Optional[SemanticNetworkVisualizer] = None

_global_analytics_visualizer: Optional[AnalyticsVisualizer] = None
_global_temporal_visualizer: Optional[TemporalVisualizer] = None


def _get_kg_visualizer(**config) -> KGVisualizer:
    """Get or create global KGVisualizer instance."""
    global _global_kg_visualizer
    if _global_kg_visualizer is None:
        cfg = visualization_config.get_all()
        cfg.update(config)
        _global_kg_visualizer = KGVisualizer(**cfg)
    return _global_kg_visualizer


def _get_ontology_visualizer(**config) -> OntologyVisualizer:
    """Get or create global OntologyVisualizer instance."""
    global _global_ontology_visualizer
    if _global_ontology_visualizer is None:
        cfg = visualization_config.get_all()
        cfg.update(config)
        _global_ontology_visualizer = OntologyVisualizer(**cfg)
    return _global_ontology_visualizer


def _get_embedding_visualizer(**config) -> EmbeddingVisualizer:
    """Get or create global EmbeddingVisualizer instance."""
    global _global_embedding_visualizer
    if _global_embedding_visualizer is None:
        cfg = visualization_config.get_all()
        cfg.update(config)
        _global_embedding_visualizer = EmbeddingVisualizer(**cfg)
    return _global_embedding_visualizer


def _get_semantic_network_visualizer(**config) -> SemanticNetworkVisualizer:
    """Get or create global SemanticNetworkVisualizer instance."""
    global _global_semantic_network_visualizer
    if _global_semantic_network_visualizer is None:
        cfg = visualization_config.get_all()
        cfg.update(config)
        _global_semantic_network_visualizer = SemanticNetworkVisualizer(**cfg)
    return _global_semantic_network_visualizer


def _get_analytics_visualizer(**config) -> AnalyticsVisualizer:
    """Get or create global AnalyticsVisualizer instance."""
    global _global_analytics_visualizer
    if _global_analytics_visualizer is None:
        cfg = visualization_config.get_all()
        cfg.update(config)
        _global_analytics_visualizer = AnalyticsVisualizer(**cfg)
    return _global_analytics_visualizer


def _get_temporal_visualizer(**config) -> TemporalVisualizer:
    """Get or create global TemporalVisualizer instance."""
    global _global_temporal_visualizer
    if _global_temporal_visualizer is None:
        cfg = visualization_config.get_all()
        cfg.update(config)
        _global_temporal_visualizer = TemporalVisualizer(**cfg)
    return _global_temporal_visualizer


def visualize_kg(
    graph: Dict[str, Any],
    output: str = "interactive",
    file_path: Optional[Union[str, Path]] = None,
    method: str = "default",
    **options,
) -> Optional[Any]:
    """
    Visualize knowledge graph.

    Args:
        graph: Knowledge graph dictionary with entities and relationships
        output: Output type ("interactive", "html", "png", "svg")
        file_path: Output file path (required for non-interactive)
        method: Visualization method ("default", "network", "communities", "centrality")
        **options: Additional visualization options

    Returns:
        Visualization figure or None
    """
    # Check for custom method
    custom_method = method_registry.get("kg", method)
    if custom_method:
        return custom_method(graph, output=output, file_path=file_path, **options)

    # Use default method
    viz = _get_kg_visualizer(**options)

    if method == "network" or method == "default":
        return viz.visualize_network(
            graph, output=output, file_path=file_path, **options
        )
    elif method == "communities":
        communities = options.pop("communities", {})
        return viz.visualize_communities(
            graph, communities, output=output, file_path=file_path, **options
        )
    elif method == "centrality":
        centrality = options.pop("centrality", {})
        centrality_type = options.pop("centrality_type", "degree")
        return viz.visualize_centrality(
            graph,
            centrality,
            centrality_type=centrality_type,
            output=output,
            file_path=file_path,
            **options,
        )
    else:
        return viz.visualize_network(
            graph, output=output, file_path=file_path, **options
        )


def visualize_ontology(
    ontology: Dict[str, Any],
    output: str = "interactive",
    file_path: Optional[Union[str, Path]] = None,
    method: str = "default",
    **options,
) -> Optional[Any]:
    """
    Visualize ontology.

    Args:
        ontology: Ontology dictionary, SemanticNetwork, or ontology generator result
        output: Output type
        file_path: Output file path
        method: Visualization method ("default", "hierarchy", "properties", "structure")
        **options: Additional options

    Returns:
        Visualization figure or None
    """
    # Check for custom method
    custom_method = method_registry.get("ontology", method)
    if custom_method:
        return custom_method(ontology, output=output, file_path=file_path, **options)

    # Use default method
    viz = _get_ontology_visualizer(**options)

    if method == "hierarchy" or method == "default":
        return viz.visualize_hierarchy(
            ontology, output=output, file_path=file_path, **options
        )
    elif method == "properties":
        return viz.visualize_properties(
            ontology, output=output, file_path=file_path, **options
        )
    elif method == "structure":
        return viz.visualize_structure(
            ontology, output=output, file_path=file_path, **options
        )
    else:
        return viz.visualize_hierarchy(
            ontology, output=output, file_path=file_path, **options
        )


def visualize_embeddings(
    embeddings: np.ndarray,
    labels: Optional[List[str]] = None,
    output: str = "interactive",
    file_path: Optional[Union[str, Path]] = None,
    method: str = "default",
    **options,
) -> Optional[Any]:
    """
    Visualize embeddings.

    Args:
        embeddings: Embedding matrix (n_samples, n_features)
        labels: Optional labels for coloring points
        output: Output type
        file_path: Output file path
        method: Visualization method ("default", "2d_projection", "3d_projection", "similarity", "clustering")
        **options: Additional options

    Returns:
        Visualization figure or None
    """
    # Check for custom method
    custom_method = method_registry.get("embedding", method)
    if custom_method:
        return custom_method(
            embeddings, labels=labels, output=output, file_path=file_path, **options
        )

    # Use default method
    viz = _get_embedding_visualizer(**options)

    if method == "2d_projection" or method == "default":
        reduction_method = options.pop(
            "reduction_method",
            visualization_config.get("dimension_reduction_method", "umap"),
        )
        return viz.visualize_2d_projection(
            embeddings,
            labels,
            method=reduction_method,
            output=output,
            file_path=file_path,
            **options,
        )
    elif method == "3d_projection":
        reduction_method = options.pop(
            "reduction_method",
            visualization_config.get("dimension_reduction_method", "umap"),
        )
        return viz.visualize_3d_projection(
            embeddings,
            labels,
            method=reduction_method,
            output=output,
            file_path=file_path,
            **options,
        )
    elif method == "similarity":
        return viz.visualize_similarity_heatmap(
            embeddings, labels, output=output, file_path=file_path, **options
        )
    elif method == "clustering":
        cluster_labels = options.pop("cluster_labels", None)
        reduction_method = options.pop(
            "reduction_method",
            visualization_config.get("dimension_reduction_method", "umap"),
        )
        return viz.visualize_clustering(
            embeddings,
            cluster_labels,
            method=reduction_method,
            output=output,
            file_path=file_path,
            **options,
        )
    else:
        reduction_method = options.pop(
            "reduction_method",
            visualization_config.get("dimension_reduction_method", "umap"),
        )
        return viz.visualize_2d_projection(
            embeddings,
            labels,
            method=reduction_method,
            output=output,
            file_path=file_path,
            **options,
        )


def visualize_semantic_network(
    semantic_network: Any,
    output: str = "interactive",
    file_path: Optional[Union[str, Path]] = None,
    method: str = "default",
    **options,
) -> Optional[Any]:
    """
    Visualize semantic network.

    Args:
        semantic_network: SemanticNetwork object, dict, or semantic model
        output: Output type
        file_path: Output file path
        method: Visualization method ("default", "network", "node_types", "edge_types")
        **options: Additional options

    Returns:
        Visualization figure or None
    """
    # Check for custom method
    custom_method = method_registry.get("semantic_network", method)
    if custom_method:
        return custom_method(
            semantic_network, output=output, file_path=file_path, **options
        )

    # Use default method
    viz = _get_semantic_network_visualizer(**options)

    if method == "network" or method == "default":
        return viz.visualize_network(
            semantic_network, output=output, file_path=file_path, **options
        )
    elif method == "node_types":
        return viz.visualize_node_types(
            semantic_network, output=output, file_path=file_path, **options
        )
    elif method == "edge_types":
        return viz.visualize_edge_types(
            semantic_network, output=output, file_path=file_path, **options
        )
    else:
        return viz.visualize_network(
            semantic_network, output=output, file_path=file_path, **options
        )


def visualize_analytics(
    analytics_data: Dict[str, Any],
    output: str = "interactive",
    file_path: Optional[Union[str, Path]] = None,
    method: str = "default",
    **options,
) -> Optional[Any]:
    """
    Visualize graph analytics.

    Args:
        analytics_data: Analytics data dictionary (graph, centrality, communities, etc.)
        output: Output type
        file_path: Output file path
        method: Visualization method ("default", "centrality", "communities", "connectivity", "degree_distribution")
        **options: Additional options

    Returns:
        Visualization figure or None
    """
    # Check for custom method
    custom_method = method_registry.get("analytics", method)
    if custom_method:
        return custom_method(
            analytics_data, output=output, file_path=file_path, **options
        )

    # Use default method
    viz = _get_analytics_visualizer(**options)

    if method == "centrality" or method == "default":
        centrality = analytics_data.get("centrality", {})
        centrality_type = options.pop("centrality_type", "degree")
        top_n = options.pop("top_n", 20)
        return viz.visualize_centrality_rankings(
            centrality,
            centrality_type=centrality_type,
            top_n=top_n,
            output=output,
            file_path=file_path,
            **options,
        )
    elif method == "communities":
        graph = analytics_data.get("graph", {})
        communities = analytics_data.get("communities", {})
        return viz.visualize_community_structure(
            graph, communities, output=output, file_path=file_path, **options
        )
    elif method == "connectivity":
        connectivity = analytics_data.get("connectivity", {})
        return viz.visualize_connectivity(
            connectivity, output=output, file_path=file_path, **options
        )
    elif method == "degree_distribution":
        graph = analytics_data.get("graph", {})
        return viz.visualize_degree_distribution(
            graph, output=output, file_path=file_path, **options
        )
    else:
        centrality = analytics_data.get("centrality", {})
        return viz.visualize_centrality_rankings(
            centrality,
            centrality_type="degree",
            top_n=20,
            output=output,
            file_path=file_path,
            **options,
        )


def visualize_temporal(
    temporal_data: Dict[str, Any],
    output: str = "interactive",
    file_path: Optional[Union[str, Path]] = None,
    method: str = "default",
    **options,
) -> Optional[Any]:
    """
    Visualize temporal data.

    Args:
        temporal_data: Temporal data dictionary with timestamps and changes
        output: Output type
        file_path: Output file path
        method: Visualization method ("default", "timeline", "patterns", "snapshot_comparison", "evolution")
        **options: Additional options

    Returns:
        Visualization figure or None
    """
    # Check for custom method
    custom_method = method_registry.get("temporal", method)
    if custom_method:
        return custom_method(
            temporal_data, output=output, file_path=file_path, **options
        )

    # Use default method
    viz = _get_temporal_visualizer(**options)

    if method == "timeline" or method == "default":
        return viz.visualize_timeline(
            temporal_data, output=output, file_path=file_path, **options
        )
    elif method == "patterns":
        patterns = options.pop("patterns", temporal_data.get("patterns", {}))
        return viz.visualize_temporal_patterns(
            patterns, output=output, file_path=file_path, **options
        )
    elif method == "snapshot_comparison":
        snapshots = options.pop("snapshots", temporal_data.get("snapshots", []))
        return viz.visualize_snapshot_comparison(
            snapshots, output=output, file_path=file_path, **options
        )
    elif method == "evolution":
        metrics_history = temporal_data.get("metrics_history", [])
        timestamps = temporal_data.get("timestamps", [])
        return viz.visualize_metrics_evolution(
            metrics_history, timestamps, output=output, file_path=file_path, **options
        )
    else:
        return viz.visualize_timeline(
            temporal_data, output=output, file_path=file_path, **options
        )


def get_visualization_method(task: str, method_name: str) -> Optional[Any]:
    """
    Get visualization method by task and name.

    Args:
        task: Task type (kg, ontology, embedding, semantic_network, analytics, temporal)
        method_name: Method name

    Returns:
        Method function or None if not found
    """
    return method_registry.get(task, method_name)


def list_available_methods(task: Optional[str] = None) -> Dict[str, List[str]]:
    """
    List available visualization methods.

    Args:
        task: Optional task type to filter by

    Returns:
        Dictionary mapping task types to lists of method names
    """
    return method_registry.list_all(task)
